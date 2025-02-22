from database.mongo import client as mongo_client
from keys.keys import environment, openai_api_key, cohere_api_key
from ultraconfiguration import UltraConfig
from ultraprint.logging import logger
from bson import ObjectId, errors
from openai import OpenAI
import cohere
from typing import Generator
from llm.prompts import format_context, make_basic_prompt, format_system_message, make_system_injection_prompt
from database.chroma import search_documents
from llm.sessions import update_session_history, get_recent_history
from llm.tools import execute_tools  # Update import
from concurrent.futures import ThreadPoolExecutor
from llm.decision import analyze_for_memory, summarize_chat_history
from datetime import datetime
from llm.memory import get_memory, update_memory
from llm.sessions import get_team_session_history, update_team_session_history

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
    """
    Get relevant context using collection IDs.

    Args:
        agent_id (str): The ID of the agent.
        query (str): The query to search for.
        session_id (str): The ID of the session.

    Returns:
        list: A list of relevant context results.
    """
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
    """
    Convert OpenAI format history to Cohere format.

    Args:
        history (list): A list of chat history messages in OpenAI format.

    Returns:
        list: A list of chat history messages in Cohere format.
    """
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
    """
    Chat with OpenAI models (non-streaming).

    Args:
        agent_id (str): The ID of the agent.
        messages (list): A list of messages to send to the model.

    Returns:
        str: The response from the OpenAI model.
    """
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
        log.error("OpenAI chat error: %s", str(e))
        raise

def chat_with_openai_stream(agent_id: str, messages: list):
    """
    Chat with OpenAI models (streaming).

    Args:
        agent_id (str): The ID of the agent.
        messages (list): A list of messages to send to the model.

    Yields:
        str: A stream of responses from the OpenAI model.
    """
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
    """
    Chat with Cohere models (non-streaming).

    Args:
        agent_id (str): The ID of the agent.
        messages (list): A list of messages to send to the model.

    Returns:
        str: The response from the Cohere model.
    """
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
    """
    Chat with Cohere models (streaming).

    Args:
        agent_id (str): The ID of the agent.
        messages (list): A list of messages to send to the model.

    Yields:
        str: A stream of responses from the Cohere model.
    """
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
    """
    Wrap the streaming response to yield text first, then optional metadata.

    Args:
        session_id (str): The ID of the session.
        response_stream: The stream of responses.
        metadata (dict, optional): Additional metadata to include. Defaults to None.

    Yields:
        str: A stream of text and metadata.
    """
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
    """
    Generator to stream a single sentence.

    Args:
        sentence (str): The sentence to stream.

    Yields:
        str: The sentence.
    """
    yield sentence

def verify_session_access(session_id: str, user_id: str = None) -> bool:
    """
    Verify if user has access to the session.

    Args:
        session_id (str): The ID of the session.
        user_id (str, optional): The ID of the user. Defaults to None.

    Returns:
        bool: True if the user has access, False otherwise.
    """
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

#* Main chat function --------------------------------------------------------
def chat(
    agent_id: str,
    session_id: str,
    message: str,
    stream: bool = False,
    use_rag: bool = True,
    user_id: str = None,
    include_rich_response: bool = True
) -> Generator[str, None, None] | str:
    """
    Main chat function that handles both models and RAG.

    Args:
        agent_id (str): The ID of the agent.
        session_id (str): The ID of the session.
        message (str): The message to send.
        stream (bool, optional): Whether to use streaming. Defaults to False.
        use_rag (bool, optional): Whether to use RAG. Defaults to True.
        user_id (str, optional): The ID of the user. Defaults to None.
        include_rich_response (bool, optional): Whether to include rich response. Defaults to True.

    Returns:
        Generator[str, None, None] | str: The response from the chat function.
    """
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
        log.error("Error getting recent history: %s", str(e))
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
        log.error("Error analyzing tools and memory: %s", str(e))
        tool_text = ""
        tool_metadata = {}
        tool_used = []
        tool_not_used = []
        tool_results = []

    # Get relevant context if RAG is enabled
    try:
        context_results = get_relevant_context(agent_id, message, session_id) if use_rag else []
    except Exception as e:
        log.error("Error getting context: %s", str(e))
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
        log.error("Error formatting context: %s", str(e))
        formatted_context = ""

    #* Format basic prompt
    try:
        prompt = make_basic_prompt(agent["name"], agent["role"], agent["capabilities"], agent["rules"])
    except Exception as e:
        log.error("Error making basic prompt: %s", str(e))
        prompt = ""

    #* Format system message
    try:
        system_message = format_system_message(prompt, formatted_context, tool_text)
    except Exception as e:
        log.error("Error formatting system message: %s", str(e))
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
        log.error("Error updating session history: %s", str(e))

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
        log.error("Chat error: %s", str(e))
        fallback_message = "I'm sorry, I'm taking a break right now. Please try again later."
        if stream:
            return handle_stream_response(session_id, stream_generator(fallback_message))
        else:
            return fallback_message

#! Team chat functions -------------------------------------------------------
#* Basic team chat functions -------------------------------------------------
def handle_team_stream_response(session_id: str, agent_id: str, response_stream, metadata=None, summary=False):
    """
    Stream response with a prepended agent tag.

    Args:
        session_id (str): The ID of the session.
        agent_id (str): The ID of the agent.
        response_stream: The stream of responses.
        metadata (dict, optional): Additional metadata to include. Defaults to None.
        summary (bool, optional): Whether the response is a summary. Defaults to False.

    Yields:
        str: A stream of text and metadata.
    """
    if summary:
        prefix = "[summary]\n"
        yield prefix
    else:
        prefix = f"[agent {agent_id}]\n"
        yield prefix
    full_response = ""
    for chunk in response_stream:
        if isinstance(chunk, str):
            full_response += chunk
            yield chunk
        else:
            if hasattr(chunk.choices[0].delta, 'content'):
                content = chunk.choices[0].delta.content
                if content:
                    full_response += content
                    yield content
    # Update team session history with full response and metadata
    update_team_session_history(session_id, agent_id, "assistant", full_response, metadata=metadata, summary=summary)
    if metadata:
        yield f"\n[metadata]={metadata}"

def each_team_agent_chat(
    agent_id: str,
    session_id: str,
    message: str = "",
    stream: bool = False,
    use_rag: bool = True,
    user_id: str = None,
    include_rich_response: bool = True,
    system_msg_injection: str = None
):
    """
    Handle chat for each team agent.

    Args:
        agent_id (str): The ID of the agent.
        session_id (str): The ID of the session.
        message (str, optional): The message to send. Defaults to "".
        stream (bool, optional): Whether to use streaming. Defaults to False.
        use_rag (bool, optional): Whether to use RAG. Defaults to True.
        user_id (str, optional): The ID of the user. Defaults to None.
        include_rich_response (bool, optional): Whether to include rich response. Defaults to True.
        system_msg_injection (str, optional): System message injection. Defaults to None.

    Returns:
        Generator[str, None, None] | str: The response from the chat function.
    """
    # Save original message input
    provided_message = message
    db = mongo_client.ai.agents
    agent = db.find_one({"_id": ObjectId(agent_id)})
    if not agent:
        raise ValueError("Agent not found")

    # Get recent history and add system message
    try:
        history_response = get_team_session_history(session_id, user_id, limit=agent.get("max_history", 10))
        history_messages = history_response.get("history", [])
        processed_messages = []
        for msg in history_messages:
            role = msg["role"]
            content = msg["content"]
            agent_name = msg.get("agent_name")
            if msg.get("type") == "summary":
                content = f"[Summary]: {content}"
            elif agent_name:
                content = f"[{agent_name}]: {content}"  # Modification point as requested
            processed_messages.append({"role": role, "content": content})
        messages = processed_messages
    except Exception as e:
        log.error("Error getting recent history: %s", str(e))
        messages = []
    
    # If no new message was provided, extract the last message from history and use it.
    if not provided_message and messages:
        message = messages[-1]["content"]
    
    # Parallel execution of tool analysis and memory analysis
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            log.debug("Analyzing tool need and memory storage")
            log.debug("Agent tools: %s", agent["tools"])
            tool_future = executor.submit(execute_tools, agent, message, messages)
            if provided_message:
                memory_future = executor.submit(analyze_for_memory, message)
                memory_result = memory_future.result()
            else:
                memory_result = {"to_remember": []}
            if memory_result.get("to_remember"):
                if provided_message:
                    log.debug("Adding memory items: %s", memory_result["to_remember"])
                    update_memory(agent_id, user_id, agent.get("max_memory_size", 10), memory_result["to_remember"])
            tool_result = tool_future.result()
            tool_text = tool_result.get("text", "")
            tool_metadata = tool_result.get("metadata", {})
            tool_used = tool_metadata.get("used", [])
            tool_not_used = tool_metadata.get("not_used", [])
            tool_results = tool_metadata.get("results", [])
    except Exception as e:
        log.error("Error analyzing tools and memory: %s", str(e))
        tool_text = ""
        tool_metadata = {}
        tool_used = []
        tool_not_used = []
        tool_results = []
    
    # Get relevant context if RAG is enabled
    try:
        context_results = get_relevant_context(agent_id, message, session_id) if use_rag else []
    except Exception as e:
        log.error("Error getting context: %s", str(e))
        context_results = []
    
    try:
        if provided_message:
            memory_items = get_memory(agent_id, user_id)
        else:
            memory_items = []
    except Exception:
        memory_items = []
    
    # Format all messages
    #* Format context
    try:
        formatted_context = format_context(context_results, memory_items)
    except Exception as e:
        log.error("Error formatting context: %s", str(e))
        formatted_context = ""

    #* Format basic prompt
    try:
        prompt = make_basic_prompt(agent["name"], agent["role"], agent["capabilities"], agent["rules"])
    except Exception as e:
        log.error("Error making basic prompt: %s", str(e))
        prompt = ""

    #* Format system message
    try:
        system_message = format_system_message(prompt, formatted_context, tool_text)
    except Exception as e:
        log.error("Error formatting system message: %s", str(e))
        system_message = ""
    
    # Make sure system message and messages are strings
    system_message = str(system_message)

    # Inject system message if provided
    if system_msg_injection:
        system_message = system_message + "\n" + str(system_msg_injection)

    message = str(message)

    # Add system message and user message
    messages.extend([
        {"role": "system", "content": system_message},
        {"role": "user", "content": message}
    ])

    # Only update history if a new message was supplied.
    if provided_message:
        try:
            update_team_session_history(session_id, agent_id, "user", message)
        except Exception as e:
            log.error("Error updating session history: %s", str(e))

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
                # Use the new team streaming handler instead of handle_stream_response
                return handle_team_stream_response(session_id, agent_id, response, metadata=tool_info)
            else:
                return handle_team_stream_response(session_id, agent_id, response)
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
                update_team_session_history(session_id, agent_id, "assistant", final_response, metadata=tool_info)
            else:
                update_team_session_history(session_id, agent_id, "assistant", final_response)

            if include_rich_response:
                return {
                    "agent_id": agent_id,
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
        log.error("Chat error: %s", str(e))
        fallback_message = "I'm sorry, I'm taking a break right now. Please try again later."
        if stream:
            return handle_team_stream_response(session_id, agent_id, stream_generator(fallback_message))
        else:
            return fallback_message

#? Basic team chat function --------------------------------------------------
def team_chat(session_id: str, message: str, stream: bool = False, use_rag: bool = True, user_id: str = None, include_rich_response: bool = True):
    """
    For a team session, have each selected agent answer the question sequentially.
    In non-stream mode, returns a dict with responses and an aggregated conversation.
    In stream mode, returns a generator that yields each agent's response.

    Args:
        session_id (str): The ID of the session.
        message (str): The message to send.
        stream (bool, optional): Whether to use streaming. Defaults to False.
        use_rag (bool, optional): Whether to use RAG. Defaults to True.
        user_id (str, optional): The ID of the user. Defaults to None.
        include_rich_response (bool, optional): Whether to include rich response. Defaults to True.

    Returns:
        dict | Generator[str, None, None]: The responses from the team chat function.
    """
    from bson import ObjectId
    db = mongo_client.ai
    session = db.sessions.find_one({"_id": ObjectId(session_id)})
    if not session:
        raise ValueError("Session not found")
    if session.get("session_type") != "team":
        raise ValueError("Not a team session")
    team_agents = session.get("team_agents", [])
    if not team_agents:
        raise ValueError("No team agents found in session")
    
    #all agents
    all_agents_name = []
    for agent in team_agents:
        agent_name = agent.get("agent_name")
        all_agents_name.append(agent_name)

    if not stream:
        responses = {}
        conversation_lines = []
        i = 0
        for agent in team_agents:
            
            agent_id = agent["agent_id"]
            agent_name = agent.get("agent_name", f"Agent {agent_id}")

            system_prompt_injection = make_system_injection_prompt(all_agents_name, agent_name)
            response = each_team_agent_chat(
                agent_id=agent_id,
                session_id=session_id,
                message=message if i == 0 else None,  # Only provide message to first agent
                stream=False,
                use_rag=use_rag,
                user_id=user_id,
                include_rich_response=include_rich_response,
                system_msg_injection=system_prompt_injection
            )
            i += 1
            responses[agent_id] = response
            conversation_lines.append(f"[Agent {agent_id}] : {response}")
        conversation = "\n".join(conversation_lines)

        history_response = get_team_session_history(session_id, user_id, limit=i + 1)
        summary = summarize_chat_history(history_response.get("history", [])).get("summary", "")
        if summary:
            responses["summary"] = summary
            conversation += f"\nSummary: {summary}"
            update_team_session_history(session_id, None, "assistant", summary, summary=True)
        return {"responses": responses, "conversation": conversation}
    else:
        def stream_generator_team():
            i = 0
            for agent in team_agents:
                
                agent_id = agent["agent_id"]
                agent_name = agent.get("agent_name", f"Agent {agent_id}")
                
                system_prompt_injection = make_system_injection_prompt(all_agents_name, agent_name)
                response_gen = each_team_agent_chat(
                    agent_id=agent_id,
                    session_id=session_id,
                    message=message if i == 0 else None,  # Only provide message to first agent
                    stream=True,
                    use_rag=use_rag,
                    user_id=user_id,
                    include_rich_response=include_rich_response,
                    system_msg_injection=system_prompt_injection
                )
                i += 1
                for chunk in response_gen:
                    yield chunk
                yield "\n"  # Separate agents' responses
            # get complete history
            history_response = get_team_session_history(session_id, user_id, limit=i + 1)
            summary = summarize_chat_history(history_response.get("history", [])).get("summary", "")
            if summary:
                #handle_team_stream_response to add the summary
                yield from handle_team_stream_response(session_id, None, stream_generator(summary), summary=True)

        return stream_generator_team()

def team_chat_managed(session_id: str, message: str, stream: bool = False, use_rag: bool = True,
                        user_id: str = None, include_rich_response: bool = True):
    """
    Managed team chat: first, use team_managed_decision to determine the order of agents,
    then execute the agents in that order. Otherwise, behavior is similar to team_chat.

    Args:
        session_id (str): The ID of the session.
        message (str): The message to send.
        stream (bool, optional): Whether to use streaming. Defaults to False.
        use_rag (bool, optional): Whether to use RAG. Defaults to True.
        user_id (str, optional): The ID of the user. Defaults to None.
        include_rich_response (bool, optional): Whether to include rich response. Defaults to True.

    Returns:
        dict | Generator[str, None, None]: The responses from the managed team chat function.
    """
    from bson import ObjectId
    from llm.decision import team_managed_decision  # new import for managed decision

    db = mongo_client.ai
    session = db.sessions.find_one({"_id": ObjectId(session_id)})
    if not session:
        raise ValueError("Session not found")
    if session.get("session_type") != "team-managed":
        raise ValueError("Not a team session")
    team_agents = session.get("team_agents", [])
    if not team_agents:
        raise ValueError("No team agents found in session")
    
    # Original team_agents contains only id and name; load full agent details.
    full_team_agents = []
    for agent in team_agents:
        agent_id = agent.get("agent_id")
        full_agent = db.agents.find_one({"_id": ObjectId(agent_id)})
        if full_agent:
            full_agent["agent_id"] = str(full_agent["_id"])
            full_team_agents.append(full_agent)
    if not full_team_agents:
        raise ValueError("Could not load full team agent details")
    
    #all agents
    all_agents_name = []
    for agent in team_agents:
        agent_name = agent.get("agent_name")
        all_agents_name.append(agent_name)

    # Create a reduced list containing only 'agent_id' and 'role'
    decision_agents = [{
        agent["agent_id"]: agent["role"]
    } for agent in full_team_agents]

    # Retrieve team session history
    history_response = get_team_session_history(session_id, user_id, limit=len(team_agents) + 1)
    chat_history = history_response.get("history", [])

    # Determine the execution order using the managed decision function
    decision_result = team_managed_decision(message, chat_history, all_agents=decision_agents)
    agent_order = decision_result.get("agent_order", [])
    if not agent_order:
        # fallback to original order if decision did not return one
        agent_order = [agent["agent_id"] for agent in team_agents]

    if not stream:
        responses = {}
        conversation_lines = []
        for idx, agent_id in enumerate(agent_order):
            # Locate the agent's details for display purposes
            agent_info = next((a for a in team_agents if a["agent_id"] == agent_id), {"agent_name": f"Agent {agent_id}"})
            agent_name = agent_info.get("agent_name", f"Agent {agent_id}")
            system_prompt_injection = make_system_injection_prompt(all_agents_name, agent_name)

            agent_message = message if idx == 0 else None
            response = each_team_agent_chat(
                agent_id=agent_id,
                session_id=session_id,
                message=agent_message,
                stream=False,
                use_rag=use_rag,
                user_id=user_id,
                include_rich_response=include_rich_response,
                system_msg_injection=system_prompt_injection
            )
            responses[agent_id] = response
            conversation_lines.append(f"[Agent {agent_id}] : {response}")
        conversation = "\n".join(conversation_lines)

        # Update summary from team session history
        history_response = get_team_session_history(session_id, user_id, limit=len(team_agents) + 1)
        summary = summarize_chat_history(history_response.get("history", [])).get("summary", "")
        if summary:
            responses["summary"] = summary
            conversation += f"\nSummary: {summary}"
            update_team_session_history(session_id, None, "assistant", summary, summary=True)
        return {"responses": responses, "conversation": conversation}
    else:
        def stream_generator_team_managed():
            for idx, agent_id in enumerate(agent_order):

                agent_info = next((a for a in team_agents if a["agent_id"] == agent_id), {"agent_name": f"Agent {agent_id}"})
                agent_name = agent_info.get("agent_name", f"Agent {agent_id}")
                system_prompt_injection = make_system_injection_prompt(all_agents_name, agent_name)

                agent_message = message if idx == 0 else None
                response_gen = each_team_agent_chat(
                    agent_id=agent_id,
                    session_id=session_id,
                    message=agent_message,
                    stream=True,
                    use_rag=use_rag,
                    user_id=user_id,
                    include_rich_response=include_rich_response,
                    system_msg_injection=system_prompt_injection
                )
                for chunk in response_gen:
                    yield chunk
                yield "\n"  # Separate agents' responses
            # After agents, update and stream summary if available
            history_response = get_team_session_history(session_id, user_id, limit=len(team_agents) + 1)
            summary = summarize_chat_history(history_response.get("history", [])).get("summary", "")
            if summary:
                yield from handle_team_stream_response(session_id, None, stream_generator(summary), summary=True)
        return stream_generator_team_managed()

def team_chat_flow(session_id: str, message: str, stream: bool = False, use_rag: bool = True,
                    user_id: str = None, include_rich_response: bool = True, max_steps: int = 50):
    """
    Flow-based team chat where next agent is decided based on conversation context.
    Limits the maximum number of agent responses to prevent infinite loops.

    Args:
        session_id (str): The ID of the session.
        message (str): The message to send.
        stream (bool, optional): Whether to use streaming. Defaults to False.
        use_rag (bool, optional): Whether to use RAG. Defaults to True.
        user_id (str, optional): The ID of the user. Defaults to None.
        include_rich_response (bool, optional): Whether to include rich response. Defaults to True.
        max_steps (int, optional): The maximum number of steps. Defaults to 50.

    Returns:
        dict | Generator[str, None, None]: The responses from the flow-based team chat function.
    """
    from bson import ObjectId
    from llm.decision import team_flow_decision

    db = mongo_client.ai
    session = db.sessions.find_one({"_id": ObjectId(session_id)})
    if not session:
        raise ValueError("Session not found")
    if session.get("session_type") != "team-flow":
        raise ValueError("Not a team session")
    team_agents = session.get("team_agents", [])
    if not team_agents:
        raise ValueError("No team agents found in session")

    # Load full agent details
    full_team_agents = []
    for agent in team_agents:
        agent_id = agent.get("agent_id")
        full_agent = db.agents.find_one({"_id": ObjectId(agent_id)})
        if full_agent:
            full_agent["agent_id"] = str(full_agent["_id"])
            full_team_agents.append(full_agent)

    #all agents
    all_agents_name = []
    for agent in team_agents:
        agent_name = agent.get("agent_name")
        all_agents_name.append(agent_name)

    if not stream:
        responses = {}
        conversation_lines = []
        steps_taken = 0
        
        # Initial message from user at the start
        update_team_session_history(session_id, None, "user", message)
        
        while steps_taken < max_steps:
            # Get current history for decision making
            history_response = get_team_session_history(session_id, user_id)
            chat_history = history_response.get("history", [])
            
            # Create decision agents list
            decision_agents = [{
                agent["agent_id"]: agent["role"]
            } for agent in full_team_agents]
            
            # Get next agent decision
            decision = team_flow_decision(chat_history, all_agents=decision_agents)
            next_agent = decision.get("next_agent")
            
            if not next_agent:
                break  # No more agents needed to respond
            
            steps_taken += 1
            
            # Find agent info for the selected agent
            agent_info = next((a for a in team_agents if a["agent_id"] == next_agent), 
                            {"agent_name": f"Agent {next_agent}"})
            agent_name = agent_info.get("agent_name", f"Agent {agent_id}")
            system_prompt_injection = make_system_injection_prompt(all_agents_name, agent_name)
            
            # Get agent's response
            response = each_team_agent_chat(
                agent_id=next_agent,
                session_id=session_id,
                message=None,  # Agent will use chat history
                stream=False,
                use_rag=use_rag,
                user_id=user_id,
                include_rich_response=include_rich_response,
                system_msg_injection=system_prompt_injection
            )
            
            responses[next_agent] = response
            conversation_lines.append(f"[Agent {next_agent}] : {response}")

        conversation = "\n".join(conversation_lines)
        
        # Generate and add summary - now including steps_taken + 1 for initial message
        history_response = get_team_session_history(session_id, user_id, limit=steps_taken + 1)
        summary = summarize_chat_history(history_response.get("history", [])).get("summary", "")
        if summary:
            responses["summary"] = summary
            conversation += f"\nSummary: {summary}"
            update_team_session_history(session_id, None, "assistant", summary, summary=True)
            
        return {"responses": responses, "conversation": conversation}
    else:
        def stream_generator_team_flow():
            steps_taken = 0
            # Initial message from user at the start
            update_team_session_history(session_id, None, "user", message)
            
            while steps_taken < max_steps:
                # Get current history for decision making
                history_response = get_team_session_history(session_id, user_id)
                chat_history = history_response.get("history", [])
                
                # Create decision agents list
                decision_agents = [{
                    agent["agent_id"]: agent["role"]
                } for agent in full_team_agents]
                
                # Get next agent decision
                decision = team_flow_decision(chat_history, all_agents=decision_agents)
                next_agent = decision.get("next_agent")
                
                if not next_agent:
                    break  # No more agents needed to respond
                
                steps_taken += 1

                # Find agent info for the selected agent
                agent_info = next((a for a in team_agents if a["agent_id"] == next_agent), 
                                {"agent_name": f"Agent {next_agent}"})
                agent_name = agent_info.get("agent_name", f"Agent {agent_id}")
                system_prompt_injection = make_system_injection_prompt(all_agents_name, agent_name)

                # Stream the next agent's response
                response_gen = each_team_agent_chat(
                    agent_id=next_agent,
                    session_id=session_id,
                    message=None,  # Agent will use chat history
                    stream=True,
                    use_rag=use_rag,
                    user_id=user_id,
                    include_rich_response=include_rich_response,
                    system_msg_injection=system_prompt_injection
                )
                
                for chunk in response_gen:
                    yield chunk
                yield "\n"  # Separate agents' responses
                
            # Generate and stream summary - now including steps_taken + 1 for initial message
            history_response = get_team_session_history(session_id, user_id, limit=steps_taken + 1)
            summary = summarize_chat_history(history_response.get("history", [])).get("summary", "")
            if summary:
                yield from handle_team_stream_response(session_id, None, stream_generator(summary), summary=True)
                
        return stream_generator_team_flow()


