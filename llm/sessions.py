from database.mongo import client as mongo_client
from ultraconfiguration import UltraConfig
from ultraprint.logging import logger
from datetime import datetime, timezone
from bson import ObjectId
from keys.keys import environment

#! Initialize ---------------------------------------------------------------
config = UltraConfig('config.json')
log = logger('sessions_log', 
            filename='debug/sessions.log', 
            include_extra_info=config.get("logging.include_extra_info", False), 
            write_to_file=config.get("logging.write_to_file", False), 
            log_level=config.get("logging.development_level", "DEBUG") if environment == 'development' else config.get("logging.production_level", "INFO"))

#! Chat session functions --------------------------------------------------
def create_session(agent_id: str, max_context_results: int = 1, user_id: str = None) -> str:
    """Create a new chat session for an agent with optional user ownership."""
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
        # For public agents, check if they're actually public
        elif agent_type == "public":
            pass  # Public agents are accessible to all
        # For system agents, verify they're actually system agents
        elif agent_type == "system":
            pass  # System agents are accessible to all
        else:
            raise ValueError("Invalid agent type")

    if not isinstance(max_context_results, int) or max_context_results < 1:
        raise ValueError("max_context_results must be a positive integer")
    
    session_doc = {
        "agent_id": ObjectId(agent_id),
        "history": [],
        "max_context_results": max_context_results,
        "created_at": datetime.now(timezone.utc)
    }
    if user_id:
        session_doc["user_id"] = str(user_id)  # Store as string
    
    result = db.sessions.insert_one(session_doc)
    return str(result.inserted_id)  # Return MongoDB's _id directly

def delete_session(session_id: str, user_id: str = None):
    """Delete a chat session with security check."""
    db = mongo_client.ai
    session = db.sessions.find_one({"_id": ObjectId(session_id)})  # Changed from session_id to _id
    if not session:
        raise ValueError("Session not found")
    if user_id:
        agent = db.agents.find_one({"_id": session["agent_id"]})
        if agent and "user_id" in agent and str(agent["user_id"]) != user_id:
            raise ValueError("Not authorized to delete this session")
    result = db.sessions.delete_one({"_id": ObjectId(session_id)})  # Changed from session_id to _id
    if result.deleted_count == 0:
        raise ValueError("Session not found")

def get_session(session_id: str, user_id: str = None, limit: int = 20, skip: int = 0):
    """Get details of a single session with security check and paginated history."""
    db = mongo_client.ai
    session = db.sessions.find_one({"_id": ObjectId(session_id)})  # Changed from session_id to _id
    if not session:
        raise ValueError("Session not found")
    if user_id:
        agent = db.agents.find_one({"_id": session["agent_id"]})
        if agent and "user_id" in agent and str(agent["user_id"]) != user_id:
            raise ValueError("Not authorized to view this session")
    
    # Get full history and sort by timestamp descending
    full_history = sorted(
        session.get("history", []),
        key=lambda x: x.get("timestamp", datetime.min),
        reverse=True
    )
    total_messages = len(full_history)
    
    # Create a copy of the session document and modify the history
    session_data = dict(session)
    session_data["history"] = full_history[skip:skip + limit]
    session_data["history_metadata"] = {
        "total": total_messages,
        "skip": skip,
        "limit": limit
    }
    
    return session_data

def get_session_history(session_id: str, user_id: str = None, limit: int = 20, skip: int = 0) -> list:
    """Get paginated chat history for a session with security check."""
    db = mongo_client.ai
    session = db.sessions.find_one({"_id": ObjectId(session_id)})  # Changed from session_id to _id
    if not session:
        raise ValueError("Session not found")
    if user_id:
        agent = db.agents.find_one({"_id": session["agent_id"]})
        if agent and "user_id" in agent and str(agent["user_id"]) != user_id:
            raise ValueError("Not authorized to view this session")
    
    # Sort history by timestamp descending
    history = sorted(
        session.get("history", []),
        key=lambda x: x.get("timestamp", datetime.min),
        reverse=True
    )
    total = len(history)
    paginated_history = history[skip:skip + limit]
    
    return {
        "history": paginated_history,
        "total": total,
        "skip": skip,
        "limit": limit
    }

def update_session_history(session_id: str, role: str, content: str, user_id: str = None):
    """Add message to session history with security check."""
    db = mongo_client.ai
    session = db.sessions.find_one({"_id": ObjectId(session_id)})  # Changed from session_id to _id
    if not session:
        raise ValueError("Session not found")
    if user_id:
        agent = db.agents.find_one({"_id": session["agent_id"]})
        if agent and "user_id" in agent and str(agent["user_id"]) != user_id:
            raise ValueError("Not authorized to update this session")
    db.sessions.update_one(
        {"_id": ObjectId(session_id)},  # Changed from session_id to _id
        {"$push": {"history": {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc)
        }}}
    )

def get_recent_history(session_id: str, user_id: str = None, limit: int = 20, skip: int = 0) -> list:
    """Get paginated recent chat history with security check."""
    db = mongo_client.ai
    session = db.sessions.find_one({"_id": ObjectId(session_id)})
    if not session:
        raise ValueError("Session not found")
    if user_id:
        agent = db.agents.find_one({"_id": session["agent_id"]})
        if agent and "user_id" in agent and str(agent["user_id"]) != user_id:
            raise ValueError("Not authorized to view this session")
    
    # Sort history by timestamp descending
    history = sorted(
        session.get("history", []),
        key=lambda x: x.get("timestamp", datetime.min),
        reverse=True
    )
    
    total = len(history)
    paginated_history = history[skip:skip + limit]
    
    return {
        "history": paginated_history,
        "total": total,
        "skip": skip,
        "limit": limit
    }

def get_all_sessions_for_user(user_id: str, limit: int = 20, skip: int = 0, sort_by: str = "created_at", sort_order: int = -1) -> list:
    """Get all sessions belonging to a user with pagination and sorting."""
    db = mongo_client.ai
    return list(db.sessions.find({"user_id": str(user_id)})  # Query with string
                .sort(sort_by, sort_order)
                .skip(skip)
                .limit(limit))

def get_agent_sessions_for_user(agent_id: str, user_id: str = None, limit: int = 20, skip: int = 0, sort_by: str = "created_at", sort_order: int = -1) -> list:
    """Get all sessions for a specific agent with optional user security check."""
    db = mongo_client.ai
    
    # First check if user is authorized to view this agent's sessions
    if user_id:
        agent = db.agents.find_one({"_id": ObjectId(agent_id)})
        if agent and "user_id" in agent and str(agent["user_id"]) != user_id:
            raise ValueError("Not authorized to view sessions for this agent")
    
    query = {"agent_id": ObjectId(agent_id)}
    if user_id:
        query["user_id"] = str(user_id)  # Query with string
    
    return list(db.sessions.find(query)
                .sort(sort_by, sort_order)                
                .skip(skip)                
                .limit(limit))