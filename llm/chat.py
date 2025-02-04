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
from decision import analyze_tool_need, analyze_for_memory

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
def chat_with_openai(
        
    agent_id: str,
    messages: list,
    stream: bool = False

) -> Generator[str, None, None] | str:
    
    """Chat with OpenAI models"""

    db = mongo_client.ai.agents
    agent = db.find_one({"_id": ObjectId(agent_id)})
    
    if stream:
        response = openai_client.chat.completions.create(
            model=agent["model"],
            messages=messages,
            stream=True
        )
        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    else:
        response = openai_client.chat.completions.create(
            model=agent["model"],
            messages=messages
        )
        return response.choices[0].message.content

def chat_with_cohere(
        
    agent_id: str,
    messages: list,
    stream: bool = False

) -> Generator[str, None, None] | str:
    
    """Chat with Cohere models"""

    db = mongo_client.ai.agents
    agent = db.find_one({"_id": ObjectId(agent_id)})
    
    # Convert messages to Cohere format
    chat_history, preamble = format_history_for_cohere(messages)
    
    if stream:
        response = cohere_client.chat(
            message=messages[-1]["content"],
            model=agent["model"],
            chat_history=chat_history[:-1],
            stream=True,
            preamble=preamble
        )
        for event in response:
            if event.text:
                yield event.text
    else:
        response = cohere_client.chat(
            message=messages[-1]["content"],
            model=agent["model"],
            chat_history=chat_history[:-1],
            preamble=preamble
        )
        return response.text

#! Driver function -----------------------------------------------------------
def handle_stream_response(session_id, response_stream):
    """Handle streaming response and update history"""
    full_response = ""
    for chunk in response_stream:
        # Accumulate chunks into complete message
        if hasattr(chunk, 'choices') and chunk.choices:
            content = chunk.choices[0].delta.content
            if content:
                full_response += content
        yield chunk
    
    # Update history with complete message using _id
    update_session_history(session_id, "assistant", full_response)

def chat(

    agent_id: str,
    session_id: str,  # This is now expecting MongoDB's _id
    message: str,
    stream: bool = False,
    use_rag: bool = True

) -> Generator[str, None, None] | str:
    
    """Main chat function that handles both models and RAG"""

    db = mongo_client.ai.agents
    agent = db.find_one({"_id": ObjectId(agent_id)})
    if not agent:
        raise ValueError("Agent not found")

    # Verify session exists
    session_db = mongo_client.ai.sessions
    session = session_db.find_one({"_id": ObjectId(session_id)})  # Changed from session_id to _id
    if not session:
        raise ValueError("Session not found")

    # Parallel execution of tool analysis and memory analysis
    with ThreadPoolExecutor(max_workers=2) as executor:
        tool_future = executor.submit(analyze_tool_need, message, agent["tools"])
        memory_future = executor.submit(analyze_for_memory, message)
        
        tool_result = tool_future.result()
        memory_result = memory_future.result()

    # Handle tool execution if needed
    tool_response = ""
    if tool_result.get("tools"):
        tool_response = execute_tools(tool_result["tools"])

    # Handle memory storage if needed
    if memory_result["to_remember"]:
        update_memory(agent_id, memory_result["to_remember"])

    # Get relevant context if RAG is enabled
    context_results = get_relevant_context(agent_id, message, session_id) if use_rag else []
    memory_items = agent.get("memory", [])
    
    # Format all messages
    formatted_context = format_context(context_results, memory_items)
    prompt = make_basic_prompt(agent["name"], agent["role"], agent["capabilities"], agent["rules"])
    system_message = format_system_message(prompt, formatted_context, tool_response)
    
    # Get recent history and add system message
    messages = get_recent_history(session_id, agent["max_history"])
    messages = messages + [{"role": "system", "content": system_message}]
    
    # Add current message
    messages.append({"role": "user", "content": message})

    # Update history
    #TODO: Do this in parallel
    update_session_history(session_id, "user", message)

    # Route to appropriate chat function
    if agent["model_provider"] == "openai":
        response = chat_with_openai(agent_id, messages, stream)
    else:  # cohere
        response = chat_with_cohere(agent_id, messages, stream)

    # Update history if not streaming
    if not stream:
        #TODO: Do this in parallel
        update_session_history(session_id, "assistant", response)
    else:
        return handle_stream_response(session_id, response)

    return response
