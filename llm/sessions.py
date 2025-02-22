from database.mongo import client as mongo_client
from ultraconfiguration import UltraConfig
from ultraprint.logging import logger
from datetime import datetime, timezone
from bson import ObjectId
from keys.keys import environment
from utilities.save_json import convert_objectid_to_str

# NEW HELPER: safely converts an id to string.
def safe_convert_id(value):
    """
    Safely convert a value to a string, handling ObjectId instances.

    Args:
        value: The value to convert.

    Returns:
        str: The string representation of the value.
    """
    if isinstance(value, ObjectId):
        return convert_objectid_to_str(value)
    return str(value)

#! Initialize ---------------------------------------------------------------
config = UltraConfig('config.json')
log = logger('sessions_log', 
            filename='debug/sessions.log', 
            include_extra_info=config.get("logging.include_extra_info", False), 
            write_to_file=config.get("logging.write_to_file", False), 
            log_level=config.get("logging.development_level", "DEBUG") if environment == 'development' else config.get("logging.production_level", "INFO"))

#! Chat session functions --------------------------------------------------
def create_session(agent_id: str, max_context_results: int = 1, user_id: str = None, name: str = None) -> str:
    """
    Create a new chat session for an agent.

    Args:
        agent_id (str): The ID of the agent for the session.
        max_context_results (int, optional): The maximum number of context results to retrieve. Defaults to 1.
        user_id (str, optional): The ID of the user creating the session. Defaults to None.
        name (str, optional): The name of the session. Defaults to None.

    Returns:
        str: The ID of the newly created session.

    Raises:
        ValueError: If the agent is not found or if the user is not authorized to create a session for the agent.
    """
    db = mongo_client.ai
    agent = db.agents.find_one({"_id": ObjectId(agent_id)})
    if not agent:
        raise ValueError("Agent not found")

    # Access control validation
    agent_type = agent.get("agent_type")
    if user_id:
        # For private agents, verify ownership
        if agent_type == "private":
            if "user_id" not in agent or str(agent["user_id"]) != user_id:
                raise ValueError("Not authorized to create session for this private agent")
        # For approved agents, verify approval status
        elif agent_type == "approved":
            pass  # Approved agents are accessible to all
        # For public agents, verify approval status
        elif agent_type == "public":
            pass  # Public agents are accessible to all
        # For system agents, verify system agent status
        elif agent_type == "system":
            pass  # System agents are accessible to all
        else:
            raise ValueError("Invalid agent type")

    if not isinstance(max_context_results, int) or max_context_results < 1:
        raise ValueError("max_context_results must be a positive integer")
    
    session_doc = {
        "agent_id": ObjectId(agent_id),
        "max_context_results": max_context_results,
        "created_at": datetime.now(timezone.utc),
        "name": name or "Untitled Session"  # Default name if none provided
    }
    if user_id:
        session_doc["user_id"] = str(user_id)  # Store as string
    
    result = db.sessions.insert_one(session_doc)
    return str(result.inserted_id)  # Return MongoDB's _id directly

def update_session_name(session_id: str, new_name: str, user_id: str = None):
    """
    Update the name of an existing session.

    Args:
        session_id (str): The ID of the session to update.
        new_name (str): The new name for the session.
        user_id (str, optional): The ID of the user updating the session. Defaults to None.

    Raises:
        ValueError: If the session is not found or if the user is not authorized to update the session.
    """
    db = mongo_client.ai
    session = db.sessions.find_one({"_id": ObjectId(session_id)})
    if not session:
        raise ValueError("Session not found")
    # Removed agent ownership check. Verify session ownership directly.
    if user_id and session.get("user_id") != user_id:
        raise ValueError("Not authorized to update this session")
    result = db.sessions.update_one({"_id": ObjectId(session_id)}, {"$set": {"name": new_name}})
    if result.modified_count == 0:
        raise ValueError("Failed to update session name")

def delete_session(session_id: str, user_id: str = None):
    """
    Delete a chat session.

    Args:
        session_id (str): The ID of the session to delete.
        user_id (str, optional): The ID of the user deleting the session. Defaults to None.

    Raises:
        ValueError: If the session is not found or if the user is not authorized to delete the session.
    """
    db = mongo_client.ai
    session = db.sessions.find_one({"_id": ObjectId(session_id)})  # Changed from session_id to _id
    if not session:
        raise ValueError("Session not found")
    if user_id and session.get("user_id") != user_id:
        raise ValueError("Not authorized to delete this session")
    result = db.sessions.delete_one({"_id": ObjectId(session_id)})  # Changed from session_id to _id
    if result.deleted_count == 0:
        raise ValueError("Session not found")
    db.history.delete_many({"session_id": ObjectId(session_id)})  # Clean up related history

def get_session(session_id: str, user_id: str = None, limit: int = 20, skip: int = 0):
    """
    Get details of a single session with paginated history.

    Args:
        session_id (str): The ID of the session to retrieve.
        user_id (str, optional): The ID of the user requesting the session. Defaults to None.
        limit (int, optional): The maximum number of history entries to retrieve. Defaults to 20.
        skip (int, optional): The number of history entries to skip. Defaults to 0.

    Returns:
        dict: A dictionary containing the session details and paginated history.

    Raises:
        ValueError: If the session is not found or if the user is not authorized to view the session.
    """
    db = mongo_client.ai
    session = db.sessions.find_one({"_id": ObjectId(session_id)})
    if not session:
        raise ValueError("Session not found")
        
    # Check user authorization
    if user_id and session.get("user_id") != user_id:
        raise ValueError("Not authorized to view this session")
    
    # For regular sessions, check agent authorization if agent_id exists
    agent_id = session.get("agent_id")
    
    # Create a copy and handle conversions
    session_data = dict(session)
    session_data["_id"] = safe_convert_id(session_data["_id"])
    
    # Safely convert agent_id if it exists
    if session_data.get("agent_id"):
        session_data["agent_id"] = safe_convert_id(session_data["agent_id"])
    
    # Convert team_agents if they exist
    if session_data.get("team_agents"):
        for agent in session_data["team_agents"]:
            if agent.get("agent_id"):
                agent["agent_id"] = safe_convert_id(agent["agent_id"])
    
    # Get total count first
    total = db.history.count_documents({"session_id": ObjectId(session_id)})
    
    # Get latest entries by sorting in descending order
    history_docs = list(db.history.find({"session_id": ObjectId(session_id)})
                       .sort("timestamp", -1)  # Changed to -1 for latest first
                       .skip(skip)
                       .limit(limit))
    
    # Reverse the results to maintain chronological order (oldest to newest)
    history_docs.reverse()
    for doc in history_docs:
        if "_id" in doc:
            doc["_id"] = safe_convert_id(doc["_id"])
        if "session_id" in doc:
            doc["session_id"] = safe_convert_id(doc["session_id"])
    
    session_data["history"] = history_docs
    session_data["history_metadata"] = {
        "total": total,
        "skip": skip,
        "limit": limit
    }
    
    return session_data

def get_session_history(session_id: str, user_id: str = None, limit: int = 20, skip: int = 0) -> dict:
    """
    Get paginated chat history for a session.

    Args:
        session_id (str): The ID of the session to retrieve history for.
        user_id (str, optional): The ID of the user requesting the history. Defaults to None.
        limit (int, optional): The maximum number of history entries to retrieve. Defaults to 20.
        skip (int, optional): The number of history entries to skip. Defaults to 0.

    Returns:
        dict: A dictionary containing the paginated chat history.

    Raises:
        ValueError: If the session is not found or if the user is not authorized to view the session.
    """
    db = mongo_client.ai
    session = db.sessions.find_one({"_id": ObjectId(session_id)})  # Changed from session_id to _id
    if not session:
        raise ValueError("Session not found")
    if user_id and session.get("user_id") != user_id:
        raise ValueError("Not authorized to view this session")
    
    # Convert agent_id field if present
    if "agent_id" in session:
        session["agent_id"] = safe_convert_id(session["agent_id"])
    
    # Get total count
    total = db.history.count_documents({"session_id": ObjectId(session_id)})
    
    # Get latest entries
    history_docs = list(db.history.find({"session_id": ObjectId(session_id)})
                       .sort("timestamp", -1)  # Latest first
                       .skip(skip)
                       .limit(limit))
    
    # Reverse to maintain conversation flow
    history_docs.reverse()
    for doc in history_docs:
        if "_id" in doc:
            doc["_id"] = safe_convert_id(doc["_id"])
        if "session_id" in doc:
            doc["session_id"] = safe_convert_id(doc["session_id"])
    
    return {
        "history": history_docs,
        "total": total,
        "skip": skip,
        "limit": limit
    }

def update_session_history(session_id: str, role: str, content: str, metadata: dict = None, user_id: str = None):
    """
    Add a message to the session history.

    Args:
        session_id (str): The ID of the session to update.
        role (str): The role of the message sender (e.g., "user", "assistant").
        content (str): The content of the message.
        metadata (dict, optional): Additional metadata to store with the message. Defaults to None.
        user_id (str, optional): The ID of the user updating the session. Defaults to None.

    Raises:
        ValueError: If the session is not found or if the user is not authorized to update the session.
    """
    db = mongo_client.ai
    session = db.sessions.find_one({"_id": ObjectId(session_id)})  # Changed from session_id to _id
    if not session:
        raise ValueError("Session not found")
    if user_id and session.get("user_id") != user_id:
        raise ValueError("Not authorized to update this session")
    entry = {
        "session_id": ObjectId(session_id),
        "role": role,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    if metadata:
        entry["metadata"] = metadata
    db.history.insert_one(entry)  # Instead of pushing to sessions

def get_recent_history(session_id: str, user_id: str = None, limit: int = 20, skip: int = 0) -> dict:
    """
    Get paginated recent chat history, newest first.

    Args:
        session_id (str): The ID of the session to retrieve history for.
        user_id (str, optional): The ID of the user requesting the history. Defaults to None.
        limit (int, optional): The maximum number of history entries to retrieve. Defaults to 20.
        skip (int, optional): The number of history entries to skip. Defaults to 0.

    Returns:
        dict: A dictionary containing the paginated chat history, sorted by timestamp descending.

    Raises:
        ValueError: If the session is not found or if the user is not authorized to view the session.
    """
    db = mongo_client.ai
    session = db.sessions.find_one({"_id": ObjectId(session_id)})
    if not session:
        raise ValueError("Session not found")
    if user_id and session.get("user_id") != user_id:
        raise ValueError("Not authorized to view this session")
    
    # Convert agent_id field if present
    if "agent_id" in session:
        session["agent_id"] = safe_convert_id(session["agent_id"])
    
    total = db.history.count_documents({"session_id": ObjectId(session_id)})
    
    # Already correct - keep newest first, don't reverse
    history_docs = list(db.history.find({"session_id": ObjectId(session_id)})
                    .sort("timestamp", -1)  # Most recent first
                    .skip(skip)
                    .limit(limit))
    for doc in history_docs:
        if "_id" in doc:
            doc["_id"] = safe_convert_id(doc["_id"])
        if "session_id" in doc:
            doc["session_id"] = safe_convert_id(doc["session_id"])
    
    return {
        "history": history_docs,
        "total": total,
        "skip": skip,
        "limit": limit
    }

def get_all_sessions_for_user(user_id: str, limit: int = 20, skip: int = 0, sort_by: str = "created_at", sort_order: int = -1) -> list:
    """
    Get all sessions belonging to a user with pagination and sorting.

    Args:
        user_id (str): The ID of the user to retrieve sessions for.
        limit (int, optional): The maximum number of sessions to retrieve. Defaults to 20.
        skip (int, optional): The number of sessions to skip. Defaults to 0.
        sort_by (str, optional): The field to sort the sessions by. Defaults to "created_at".
        sort_order (int, optional): The sort order (1 for ascending, -1 for descending). Defaults to -1.

    Returns:
        list: A list of sessions belonging to the user.
    """
    db = mongo_client.ai
    sessions = list(db.sessions.find({"user_id": str(user_id)})  # Query with string
                .sort(sort_by, sort_order)
                .skip(skip)
                .limit(limit))
    for s in sessions:
        s["_id"] = safe_convert_id(s["_id"])
        if "agent_id" in s:
            s["agent_id"] = safe_convert_id(s["agent_id"])
    return sessions

def get_agent_sessions_for_user(agent_id: str, user_id: str = None, limit: int = 20, skip: int = 0, sort_by: str = "created_at", sort_order: int = -1) -> list:
    """
    Get all sessions for a specific agent with optional user security check.

    Args:
        agent_id (str): The ID of the agent to retrieve sessions for.
        user_id (str, optional): The ID of the user requesting the sessions. Defaults to None.
        limit (int, optional): The maximum number of sessions to retrieve. Defaults to 20.
        skip (int, optional): The number of sessions to skip. Defaults to 0.
        sort_by (str, optional): The field to sort the sessions by. Defaults to "created_at".
        sort_order (int, optional): The sort order (1 for ascending, -1 for descending). Defaults to -1.

    Returns:
        list: A list of sessions for the specified agent.
    """
    db = mongo_client.ai
    
    query = {"agent_id": ObjectId(agent_id)}
    if user_id:
        query["user_id"] = str(user_id)  # Query with string
    
    sessions = list(db.sessions.find(query)
                .sort(sort_by, sort_order)                
                .skip(skip)                
                .limit(limit))
    for s in sessions:
        s["_id"] = safe_convert_id(s["_id"])
        if "agent_id" in s:
            s["agent_id"] = safe_convert_id(s["agent_id"])
    return sessions

def get_team_sessions_for_user(
    user_id: str,
    limit: int = 20,
    skip: int = 0,
    sort_by: str = "created_at",
    sort_order: int = -1
) -> list:
    """
    Return sessions with session_type in ['team', 'team-managed', 'team-flow'].

    Args:
        user_id (str): The ID of the user to retrieve sessions for.
        limit (int, optional): The maximum number of sessions to retrieve. Defaults to 20.
        skip (int, optional): The number of sessions to skip. Defaults to 0.
        sort_by (str, optional): The field to sort the sessions by. Defaults to "created_at".
        sort_order (int, optional): The sort order (1 for ascending, -1 for descending). Defaults to -1.

    Returns:
        list: A list of team sessions for the user.
    """
    db = mongo_client.ai
    query = {
        "user_id": str(user_id),
        "session_type": {"$in": ["team", "team-managed", "team-flow"]}
    }
    sessions = list(db.sessions.find(query)
                    .sort(sort_by, sort_order)
                    .skip(skip)
                    .limit(limit))
    for s in sessions:
        s["_id"] = safe_convert_id(s["_id"])
        if "agent_id" in s:
            s["agent_id"] = safe_convert_id(s["agent_id"])
    return sessions

def get_standalone_sessions_for_user(
    user_id: str,
    limit: int = 20,
    skip: int = 0,
    sort_by: str = "created_at",
    sort_order: int = -1
) -> list:
    """
    Return sessions without a team session_type.

    Args:
        user_id (str): The ID of the user to retrieve sessions for.
        limit (int, optional): The maximum number of sessions to retrieve. Defaults to 20.
        skip (int, optional): The number of sessions to skip. Defaults to 0.
        sort_by (str, optional): The field to sort the sessions by. Defaults to "created_at".
        sort_order (int, optional): The sort order (1 for ascending, -1 for descending). Defaults to -1.

    Returns:
        list: A list of standalone sessions for the user.
    """
    db = mongo_client.ai
    query = {
        "user_id": str(user_id),
        "$or": [
            {"session_type": {"$exists": False}},
            {"session_type": {"$nin": ["team", "team-managed", "team-flow"]}}
        ]
    }
    sessions = list(db.sessions.find(query)
                    .sort(sort_by, sort_order)
                    .skip(skip)
                    .limit(limit))
    for s in sessions:
        s["_id"] = safe_convert_id(s["_id"])
        if "agent_id" in s:
            s["agent_id"] = safe_convert_id(s["agent_id"])
    return sessions

#! Team session functions ---------------------------------------------------
def create_team_session(agent_ids: list, max_context_results: int = 1, user_id: str = None, session_type: str = "team", name: str = None) -> str:
    """
    Create a new team chat session for multiple agents, with an optional name.

    Args:
        agent_ids (list): A list of agent IDs for the session.
        max_context_results (int, optional): The maximum number of context results to retrieve. Defaults to 1.
        user_id (str, optional): The ID of the user creating the session. Defaults to None.
        session_type (str, optional): The type of the session. Defaults to "team".
        name (str, optional): The name of the session. Defaults to None.

    Returns:
        str: The ID of the newly created team session.

    Raises:
        ValueError: If any agent is not found, if the user is not authorized to use a private agent, or if the session type is invalid.
    """
    db = mongo_client.ai
    
    valid_session_types = ["team", "team-managed", "team-flow"]
    if session_type not in valid_session_types:
        raise ValueError(f"Invalid session type. Must be one of: {valid_session_types}")

    # Validate agents exist and user has access
    agents = []
    for agent_id in agent_ids:
        agent = db.agents.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        # Access control validation for private agents
        if agent.get("agent_type") == "private" and user_id:
            if "user_id" not in agent or str(agent["user_id"]) != user_id:
                raise ValueError(f"Not authorized to use private agent {agent_id}")
        
        agents.append({
            "agent_id": str(agent["_id"]),
            "agent_name": agent.get("name", f"Agent {agent_id}")
        })
    
    session_doc = {
        "session_type": session_type,
        "team_agents": agents,  # Store both ID and name
        "max_context_results": max_context_results,
        "created_at": datetime.now(timezone.utc),
        "name": name or "Untitled Team Session"  # Default name if none provided
    }
    if user_id:
        session_doc["user_id"] = str(user_id)
    
    result = db.sessions.insert_one(session_doc)
    return str(result.inserted_id)

def get_team_session_history(session_id: str, user_id: str = None, limit: int = 20, skip: int = 0) -> dict:
    """
    Get paginated chat history for a team session with agent names.

    Args:
        session_id (str): The ID of the team session to retrieve history for.
        user_id (str, optional): The ID of the user requesting the history. Defaults to None.
        limit (int, optional): The maximum number of history entries to retrieve. Defaults to 20.
        skip (int, optional): The number of history entries to skip. Defaults to 0.

    Returns:
        dict: A dictionary containing the paginated chat history.

    Raises:
        ValueError: If the session is not found or if the session is not a team session.
    """
    db = mongo_client.ai
    session = db.sessions.find_one({"_id": ObjectId(session_id)})
    if not session:
        raise ValueError("Session not found")
    if session.get("session_type") not in ["team", "team-managed", "team-flow"]:
        raise ValueError("Not a team session")
    
    total = db.history.count_documents({"session_id": ObjectId(session_id)})
    
    history_docs = list(db.history.find({"session_id": ObjectId(session_id)})
                    .sort("timestamp", -1)  # Latest first
                    .skip(skip)
                    .limit(limit))
    
    # Reverse to maintain conversation flow and convert ObjectId fields
    history_docs.reverse()
    for doc in history_docs:
        if "_id" in doc:
            doc["_id"] = safe_convert_id(doc["_id"])
        if "session_id" in doc:
            doc["session_id"] = safe_convert_id(doc["session_id"])
    
    return {
        "history": history_docs,
        "total": total,
        "skip": skip,
        "limit": limit
    }

def update_team_session_history(session_id: str, agent_id: str, role: str, content: str, metadata: dict = None, user_id: str = None, summary: bool = False):
    """
    Add a message to the team session history.

    Args:
        session_id (str): The ID of the team session to update.
        agent_id (str): The ID of the agent sending the message.
        role (str): The role of the message sender (e.g., "user", "assistant").
        content (str): The content of the message.
        metadata (dict, optional): Additional metadata to store with the message. Defaults to None.
        user_id (str, optional): The ID of the user updating the session. Defaults to None.
        summary (bool, optional): Whether the message is a summary. Defaults to False.

    Raises:
        ValueError: If the session is not found, if the session is not a team session, or if the user is not authorized to update the session.
    """
    db = mongo_client.ai
    session = db.sessions.find_one({"_id": ObjectId(session_id)})
    if not session:
        raise ValueError("Session not found")
    # Modified check to allow team, team-managed, and team-flow sessions
    if session.get("session_type") not in ["team", "team-managed", "team-flow"]:
        raise ValueError("Not a team session")
    if user_id and session.get("user_id") != user_id:
        raise ValueError("Not authorized to update this session")
    
    # Find agent name if agent_id is provided
    agent_name = None
    if agent_id:
        for agent in session.get("team_agents", []):
            if agent["agent_id"] == str(agent_id):
                agent_name = agent["agent_name"]
                break
    
    entry = {
        "session_id": ObjectId(session_id),
        "role": role,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    if agent_id:
        entry["agent_id"] = str(agent_id)
    if agent_name:
        entry["agent_name"] = agent_name
    if metadata:
        entry["metadata"] = metadata
    if summary:
        entry["type"] = "summary"
    
    db.history.insert_one(entry)  # Instead of pushing to sessions