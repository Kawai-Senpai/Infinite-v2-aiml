from database.mongo import client as mongo_client
from database.chroma import client as chroma_client
from keys.keys import environment
from ultraconfiguration import UltraConfig
from ultraprint.logging import logger
from datetime import datetime, timezone
from bson import ObjectId
from database.chroma import delete_agent_documents

#! Initialize ---------------------------------------------------------------
config = UltraConfig('config.json')
log = logger('agents_log', 
            filename='debug/agents.log', 
            include_extra_info=config.get("logging.include_extra_info", False), 
            write_to_file=config.get("logging.write_to_file", False), 
            log_level=config.get("logging.development_level", "DEBUG") if environment == 'development' else config.get("logging.production_level", "INFO"))

#! Agent functions ---------------------------------------------------------
def create_agent(name,
                role="",
                capabilities=[],
                rules=[],
                model_provider="openai",
                model="gpt-4o",
                max_history=20,
                tools=[],
                num_collections=1,
                max_memory_size=1,
                user_id=None,
                agent_type="private"):  # Add agent_type parameter
    """Create new agent with collection IDs"""

    # Validate agent type
    valid_agent_types = ["system", "public", "approved", "private"]
    if agent_type not in valid_agent_types:
        raise ValueError("Invalid agent type. Must be one of: system, public, approved, private")

    #model provider must be any of the following
    if model_provider not in config.get("supported.model_providers", ["openai"]):
        raise ValueError("Invalid model provider")
    
    #model must be supported by the model provider
    if model not in config.get("supported.models." + model_provider, []):
        raise ValueError("Invalid model")
    
    #tools must be one of the following
    valid_tools = config.get("supported.tools", ["web-search"])
    if not all(tool in valid_tools for tool in tools):
        raise ValueError("Invalid tool")

    # Validate number of collections
    if not 1 <= num_collections <= config.get("constraints.max_num_collections", 4):
        raise ValueError("Number of collections must be between 1 and 4")

    # Validate memory size
    if not isinstance(max_memory_size, int) or not 1 <= max_memory_size <= config.get("constraints.max_memory_size", 10):
        raise ValueError("max_memory_size must be an integer between 1 and 10")

    # Generate collection IDs instead of creating collections
    collection_ids = [str(ObjectId()) for _ in range(num_collections)]
    
    # Create MongoDB record
    db = mongo_client.ai.agents
    agent_data = {
        "name": name,
        "role": role,
        "capabilities": capabilities,
        "rules": rules,
        "model_provider": model_provider,
        "model": model,
        "max_history": max_history,
        "tools": tools,
        "collection_ids": collection_ids,  # Replace chroma_collections with collection_ids
        "files": [],
        "memory": [], 
        "max_memory_size": max_memory_size, 
        "created_at": datetime.now(timezone.utc),
        "agent_type": agent_type  # Replace system_agent with agent_type
    }
    
    if user_id:
        agent_data["user_id"] = user_id
    
    agent = db.agents.insert_one(agent_data)
    return agent.inserted_id

def delete_agent(agent_id):
    """Completely remove an agent and its data"""
    db = mongo_client.ai
    agent = db.agents.find_one({"_id": ObjectId(agent_id)})
    
    if not agent:
        raise ValueError("Agent not found")
    
    # Delete all documents from Chroma
    delete_agent_documents(agent_id)
    
    # Delete all associated files
    db.files.delete_many({"agent_id": ObjectId(agent_id)})
    
    # Delete agent record
    db.agents.delete_one({"_id": ObjectId(agent_id)})

def get_all_agents_for_user(user_id):
    """Return all agents that belong to a specific user."""
    db = mongo_client.ai
    return list(db.agents.find({"user_id": str(user_id)}))

def get_all_public_agents():
    """Return all agents with agent_type='public'."""
    db = mongo_client.ai
    return list(db.agents.find({"agent_type": "public"}))

def get_all_approved_agents():
    """Return all agents with agent_type='approved'."""
    db = mongo_client.ai
    return list(db.agents.find({"agent_type": "approved"}))

def get_all_system_agents():
    """Return all agents with agent_type='system'."""
    db = mongo_client.ai
    return list(db.agents.find({"agent_type": "system"}))
