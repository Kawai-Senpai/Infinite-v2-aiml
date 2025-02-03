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
    if not isinstance(max_context_results, int) or max_context_results < 1:
        raise ValueError("max_context_results must be a positive integer")
    
    session_id = str(ObjectId())
    session_doc = {
        "agent_id": ObjectId(agent_id),
        "session_id": session_id,
        "history": [],
        "max_context_results": max_context_results,
        "created_at": datetime.now(timezone.utc)
    }
    if user_id:
        session_doc["user_id"] = ObjectId(user_id)
    
    db.sessions.insert_one(session_doc)
    return session_id

def delete_session(session_id: str, user_id: str = None):
    """Delete a chat session with security check."""
    db = mongo_client.ai
    session = db.sessions.find_one({"session_id": session_id})
    if not session:
        raise ValueError("Session not found")
    if user_id:
        agent = db.agents.find_one({"_id": session["agent_id"]})
        if agent and "user_id" in agent and str(agent["user_id"]) != user_id:
            raise ValueError("Not authorized to delete this session")
    result = db.sessions.delete_one({"session_id": session_id})
    if result.deleted_count == 0:
        raise ValueError("Session not found")

def get_session_history(session_id: str, user_id: str = None) -> list:
    """Get chat history for a session with security check."""
    db = mongo_client.ai
    session = db.sessions.find_one({"session_id": session_id})
    if not session:
        raise ValueError("Session not found")
    if user_id:
        agent = db.agents.find_one({"_id": session["agent_id"]})
        if agent and "user_id" in agent and str(agent["user_id"]) != user_id:
            raise ValueError("Not authorized to view this session")
    return session["history"]

def update_session_history(session_id: str, role: str, content: str, user_id: str = None):
    """Add message to session history with security check."""
    db = mongo_client.ai
    session = db.sessions.find_one({"session_id": session_id})
    if not session:
        raise ValueError("Session not found")
    if user_id:
        agent = db.agents.find_one({"_id": session["agent_id"]})
        if agent and "user_id" in agent and str(agent["user_id"]) != user_id:
            raise ValueError("Not authorized to update this session")
    db.sessions.update_one(
        {"session_id": session_id},
        {"$push": {"history": {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc)
        }}}
    )

def get_recent_history(session_id: str, max_history: int, user_id: str = None) -> list:
    """Get recent chat history with security check."""
    db = mongo_client.ai
    session = db.sessions.find_one({"session_id": session_id})
    if not session:
        raise ValueError("Session not found")
    if user_id:
        agent = db.agents.find_one({"_id": session["agent_id"]})
        if agent and "user_id" in agent and str(agent["user_id"]) != user_id:
            raise ValueError("Not authorized to view this session")
    history = session.get("history", [])
    return history[-max_history:] if max_history > 0 else history