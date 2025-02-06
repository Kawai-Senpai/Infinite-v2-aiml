from database.mongo import client as mongo_client
from keys.keys import environment, openai_api_key, cohere_api_key
from ultraconfiguration import UltraConfig
from ultraprint.logging import logger
from bson import ObjectId
from openai import OpenAI
import cohere
from typing import Generator
from llm.prompts import format_context, make_basic_prompt, format_system_message
from database.chroma import search_documents
from llm.sessions import update_session_history, get_recent_history
from llm.tools import execute_tools  # Update import
from concurrent.futures import ThreadPoolExecutor
from llm.decision import analyze_for_memory

#! Initialize ---------------------------------------------------------------
config = UltraConfig('config.json')
log = logger('chat_log', 
            filename='debug/chat.log', 
            include_extra_info=config.get("logging.include_extra_info", False), 
            write_to_file=config.get("logging.write_to_file", False), 
            log_level=config.get("logging.development_level", "DEBUG") if environment == 'development' else config.get("logging.production_level", "INFO"))

# Initialize clients
openai_client = OpenAI(api_key=openai_api_key)
cohere_client = cohere.Client(cohere_api_key)

#! Getters and setters -------------------------------------------------------
def get_relevant_context(agent_id: str, query: str, session_id: str) -> list:
    """Get relevant context using collection IDs"""
    db = mongo_client.ai
    agent = db.agents.find_one({"_id": ObjectId(agent_id)})
    if not agent:
        raise ValueError("Agent not found")
    
    session = db.sessions.find_one({"_id": ObjectId(session_id)})  # Changed from session_id to _id
    if not session:
        raise ValueError("Session not found")
    
    max_results = session.get("max_context_results", 5)
    
    all_results = []
    for collection_id in agent["collection_ids"]:
        results = search_documents(str(agent["_id"]), collection_id, query, n_results=max_results)
        if results and results["matches"]:
            all_results.append(results)
    return all_results

def update_memory(agent_id: str, new_items: list):
    """Update agent's memory with new items, maintaining size limit"""

    db = mongo_client.ai.agents
    agent = db.find_one({"_id": ObjectId(agent_id)})
    if not agent:
        raise ValueError("Agent not found")
    
    memory = agent.get("memory", [])
    memory.extend(new_items)  # Add all new items
    
    # Keep only the most recent items based on max_memory_size
    max_size = agent.get("max_memory_size", 10)
    if len(memory) > max_size:
        memory = memory[-max_size:]
    
    db.update_one(
        {"_id": ObjectId(agent_id)},
        {"$set": {"memory": memory}}
    )

#! Core chat functions -------------------------------------------------------
#* Formatters ----------------------------------------------------------------
def format_history_for_cohere(history: list) -> list:
    """Convert OpenAI format history to Cohere format"""
    cohere_history = []
    preamble = ""
    for msg in history:
        if msg["role"] != "system":  # Skip system messages
            role = "USER" if msg["role"] == "user" else "ASSISTANT"
            cohere_history.append({
                "role": role,
                "message": msg["content"]
            })
        else:
            preamble = msg["content"]
    return cohere_history, preamble

#? Chat functions ------------------------------------------------------------
def chat_with_openai_sync(agent_id: str, messages: list):
    """Chat with OpenAI models (non-streaming)"""
    db = mongo_client.ai.agents
    agent = db.find_one({"_id": ObjectId(agent_id)})
    
    try:
        response = openai_client.chat.completions.create(
            model=agent["model"],
            messages=messages,
            stream=False
        )
        return str(response.choices[0].message.content)
    except Exception as e:
        log.error(f"OpenAI chat error: {e}")
        raise

def chat_with_openai_stream(agent_id: str, messages: list):
    """Chat with OpenAI models (streaming)"""
    db = mongo_client.ai.agents
    agent = db.find_one({"_id": ObjectId(agent_id)})
    
    response = openai_client.chat.completions.create(
        model=agent["model"],
        messages=messages,
        stream=True
    )
    for chunk in response:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content

def chat_with_cohere_sync(agent_id: str, messages: list):
    """Chat with Cohere models (non-streaming)"""
    db = mongo_client.ai.agents
    agent = db.find_one({"_id": ObjectId(agent_id)})
    
    chat_history, preamble = format_history_for_cohere(messages)
    
    response = cohere_client.chat(
        message=messages[-1]["content"],
        model=agent["model"],
        chat_history=chat_history[:-1],
        preamble=preamble
    )
    return str(response.text)

def chat_with_cohere_stream(agent_id: str, messages: list):
    """Chat with Cohere models (streaming)"""
    db = mongo_client.ai.agents
    agent = db.find_one({"_id": ObjectId(agent_id)})
    
    chat_history, preamble = format_history_for_cohere(messages)
    
    response = cohere_client.chat(
        message=messages[-1]["content"],
        model=agent["model"],
        chat_history=chat_history[:-1],
        preamble=preamble,
        stream=True
    )
    for event in response:
        if event.text:
            yield event.text

#! Driver function -----------------------------------------------------------
def handle_stream_response(session_id, response_stream):
    """Handle streaming response and update history"""
    full_response = ""
    for chunk in response_stream:
        if isinstance(chunk, str):
            full_response += chunk
            yield chunk
        else:
            # Handle OpenAI streaming response
            if hasattr(chunk.choices[0].delta, 'content'):
                content = chunk.choices[0].delta.content
                if content:
                    full_response += content
                    yield content
    
    # Update history with complete message
    update_session_history(session_id, "assistant", full_response)

def verify_session_access(session_id: str, user_id: str = None) -> bool:
    """Verify if user has access to the session"""
    if not user_id:
        return True
        
    db = mongo_client.ai
    session = db.sessions.find_one({"_id": ObjectId(session_id)})
    if not session:
        return False
        
    # Check if session belongs to user directly
    if "user_id" in session:
        return session["user_id"] == user_id  # Direct string comparison
        
    # If session doesn't have user_id, check agent ownership
    agent = db.agents.find_one({"_id": session["agent_id"]})
    if agent and "user_id" in agent:
        return agent["user_id"] == user_id  # Direct string comparison
        
    return True

def chat(
    agent_id: str,
    session_id: str,  # This is now expecting MongoDB's _id
    message: str,
    stream: bool = False,
    use_rag: bool = True,
    user_id: str = None
) -> Generator[str, None, None] | str:
    
    """Main chat function that handles both models and RAG"""

    # Verify user access first
    if not verify_session_access(session_id, user_id):
        raise ValueError("Not authorized to access this session")

    db = mongo_client.ai.agents
    agent = db.find_one({"_id": ObjectId(agent_id)})
    if not agent:
        raise ValueError("Agent not found")

    # Get recent history and add system message
    messages = get_recent_history(session_id, user_id, limit=agent["max_history"])
    if not isinstance(messages, list):
        messages = []  # Ensure messages is a list

    # Parallel execution of tool analysis and memory analysis
    with ThreadPoolExecutor(max_workers=2) as executor:
        log.debug("Analyzing tool need and memory storage")
        log.debug("Agent tools: %s", agent["tools"])

        tool_future = executor.submit(execute_tools, agent, message, messages)
        memory_future = executor.submit(analyze_for_memory, message)
        
        memory_result = memory_future.result()
        if memory_result["to_remember"]:
            log.debug("Adding memory items: %s", memory_result["to_remember"])
            update_memory(agent_id, memory_result["to_remember"])
        tool_response = tool_future.result()

    # Get relevant context if RAG is enabled
    context_results = get_relevant_context(agent_id, message, session_id) if use_rag else []
    memory_items = agent.get("memory", [])
    
    # Format all messages
    formatted_context = format_context(context_results, memory_items)
    prompt = make_basic_prompt(agent["name"], agent["role"], agent["capabilities"], agent["rules"])
    system_message = format_system_message(prompt, formatted_context, tool_response)
    
    # Add system message and user message
    messages.extend([
        {"role": "system", "content": system_message},
        {"role": "user", "content": message}
    ])

    # Update history
    #TODO: Do this in parallel
    update_session_history(session_id, "user", message)

    # Route to appropriate chat function
    if agent["model_provider"] == "openai":
        if stream:
            response = chat_with_openai_stream(agent_id, messages)
        else:
            response = chat_with_openai_sync(agent_id, messages)
    else:  # cohere
        if stream:
            response = chat_with_cohere_stream(agent_id, messages)
        else:
            response = chat_with_cohere_sync(agent_id, messages)

    if stream:
        return handle_stream_response(session_id, response)
    else:
        # If response is already a string, use it directly
        if isinstance(response, str):
            final_response = response
        # If response is a generator, join its contents
        elif hasattr(response, '__iter__'):
            final_response = ''.join(list(response))
        else:
            final_response = str(response)
            
        if not final_response:
            final_response = "No response generated"
            
        # Update history with the complete response
        update_session_history(session_id, "assistant", final_response)
        return final_response
