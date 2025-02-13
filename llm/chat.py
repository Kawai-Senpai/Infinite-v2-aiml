from database.mongo import client as mongo_client
from keys.keys import environment, openai_api_key, cohere_api_key
from ultraconfiguration import UltraConfig
from ultraprint.logging import logger
from bson import ObjectId, errors
from openai import OpenAI
import cohere
from typing import Generator
from llm.prompts import format_context, make_basic_prompt, format_system_message
from database.chroma import search_documents
from llm.sessions import update_session_history, get_recent_history
from llm.tools import execute_tools  # Update import
from concurrent.futures import ThreadPoolExecutor
from llm.decision import analyze_for_memory
from datetime import datetime
from llm.memory import get_memory, update_memory

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
def handle_stream_response(session_id, response_stream, metadata=None):
    """Wrap the streaming response to yield text first, then optional metadata"""
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
    update_session_history(session_id, "assistant", full_response, metadata=metadata)
    if metadata:
        yield f"\n[metadata]={metadata}"

def stream_generator(sentence):
    """Generator to stream a single sentence"""
    yield sentence

def verify_session_access(session_id: str, user_id: str = None) -> bool:
    """Verify if user has access to the session"""
    try:
        session_id_obj = ObjectId(session_id)
    except errors.InvalidId:
        return False  # or raise ValueError("Invalid session ID")
    if not user_id:
        return True
        
    db = mongo_client.ai
    session = db.sessions.find_one({"_id": session_id_obj})
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
    session_id: str,
    message: str,
    stream: bool = False,
    use_rag: bool = True,
    user_id: str = None,
    include_rich_response: bool = True
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
    try:
        history_response = get_recent_history(session_id, user_id, limit=agent.get("max_history", 10))
        messages = history_response.get("history", [])
        # Keep only role and content fields, remove timestamps
        messages = [{"role": msg["role"], "content": msg["content"]} for msg in messages]
    except Exception as e:
        log.error("Error getting recent history: %s", e)
        messages = []

    # Parallel execution of tool analysis and memory analysis
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            log.debug("Analyzing tool need and memory storage")
            log.debug("Agent tools: %s", agent["tools"])

            tool_future = executor.submit(execute_tools, agent, message, messages)
            memory_future = executor.submit(analyze_for_memory, message)
            
            memory_result = memory_future.result()
            if memory_result["to_remember"]:
                log.debug("Adding memory items: %s", memory_result["to_remember"])
                update_memory(agent_id, user_id, agent.get("max_memory_size", 10), memory_result["to_remember"])
            tool_result = tool_future.result()
            tool_text = tool_result.get("text", "")
            tool_metadata = tool_result.get("metadata", {})
            # NEW: Extract used, not_used, and results from tool_metadata
            tool_used = tool_metadata.get("used", [])
            tool_not_used = tool_metadata.get("not_used", [])
            tool_results = tool_metadata.get("results", [])
    except Exception as e:
        log.error("Error analyzing tools and memory: %s", e)
        tool_text = ""
        tool_metadata = {}
        tool_used = []
        tool_not_used = []
        tool_results = []

    # Get relevant context if RAG is enabled
    try:
        context_results = get_relevant_context(agent_id, message, session_id) if use_rag else []
    except Exception as e:
        log.error("Error getting context: %s", e)
        context_results = []
    
    try:
        memory_items = get_memory(agent_id, user_id)
    except Exception:
        memory_items = []
    
    # Format all messages
    #* Format context
    try:
        formatted_context = format_context(context_results, memory_items)
    except Exception as e:
        log.error("Error formatting context: %s", e)
        formatted_context = ""

    #* Format basic prompt
    try:
        prompt = make_basic_prompt(agent["name"], agent["role"], agent["capabilities"], agent["rules"])
    except Exception as e:
        log.error("Error making basic prompt: %s", e)
        prompt = ""

    #* Format system message
    try:
        system_message = format_system_message(prompt, formatted_context, tool_text)
    except Exception as e:
        log.error("Error formatting system message: %s", e)
        system_message = ""
    
    # Make sure system message and messages are strings
    system_message = str(system_message)
    message = str(message)

    # Add system message and user message
    messages.extend([
        {"role": "system", "content": system_message},
        {"role": "user", "content": message}
    ])

    # Update history
    #TODO: Do this in parallel
    try:
        update_session_history(session_id, "user", message)
    except Exception as e:
        log.error("Error updating session history: %s", e)

    try:
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
            if include_rich_response:
                tool_info = {
                    "tool_results": tool_results,
                    "tools_used": tool_used,
                    "tools_not_used": tool_not_used,
                    "memories_used": memory_items,
                    "context_results": context_results 
                }
                return handle_stream_response(session_id, response, metadata=tool_info)
            else:
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
                
            if include_rich_response:
                # Define tool_info for non-stream branch
                tool_info = {
                    "tool_results": tool_results,
                    "tools_used": tool_used,
                    "tools_not_used": tool_not_used,
                    "memories_used": memory_items,
                    "context_results": context_results  # Add context results here
                }
                update_session_history(session_id, "assistant", final_response, metadata=tool_info)
            else:
                update_session_history(session_id, "assistant", final_response)

            if include_rich_response:
                return {
                    "response": final_response,
                    "tool_results": tool_results,
                    "tools_used": tool_used,
                    "tools_not_used": tool_not_used,
                    "memories_used": memory_items,
                    "context_results": context_results  # Add context results here
                }
            else:
                return final_response
    except Exception as e:
        log.error(f"Chat error: {e}")
        fallback_message = "I'm sorry, I'm taking a break right now. Please try again later."
        if stream:
            return handle_stream_response(session_id, stream_generator(fallback_message))
        else:
            return fallback_message
