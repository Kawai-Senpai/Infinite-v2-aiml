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
def create_session(agent_id: str, max_context_results: int = 1) -> str:
    """Create a new chat session for an agent"""
    db = mongo_client.ai  # Changed from mongo_client.ai.agents
    agent = db.agents.find_one({"_id": ObjectId(agent_id)})
    if not agent:
        raise ValueError("Agent not found")
    
    if not isinstance(max_context_results, int) or max_context_results < 1:
        raise ValueError("max_context_results must be a positive integer")
    
    session_id = str(ObjectId())
    db.sessions.insert_one({
        "agent_id": ObjectId(agent_id),
        "session_id": session_id,
        "history": [],
        "max_context_results": max_context_results,
        "created_at": datetime.now(timezone.utc)
    })
    
    return session_id

def delete_session(session_id: str):
    """Delete a chat session"""
    db = mongo_client.ai.sessions
    result = db.delete_one({"session_id": session_id})
    if result.deleted_count == 0:
        raise ValueError("Session not found")

def get_session_history(session_id: str) -> list:
    """Get chat history for a session"""
    db = mongo_client.ai.sessions
    session = db.find_one({"session_id": session_id})
    if not session:
        raise ValueError("Session not found")
    return session["history"]

def update_session_history(session_id: str, role: str, content: str):
    """Add message to session history in OpenAI format"""
    db = mongo_client.ai.sessions
    db.update_one(
        {"session_id": session_id},
        {"$push": {"history": {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc)
        }}}
    )

def get_recent_history(session_id: str, max_history: int) -> list:
    """Get recent chat history in OpenAI format"""
    db = mongo_client.ai.sessions
    session = db.find_one({"session_id": session_id})
    if not session:
        raise ValueError("Session not found")
    
    history = session.get("history", [])
    return history[-max_history:] if max_history > 0 else history