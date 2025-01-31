from database.mongo import client as mongo_client
from database.chroma import client as chroma_client
from keys.keys import environment, openai_api_key
from ultraconfiguration import UltraConfig
from ultraprint.logging import logger
from datetime import datetime
from bson import ObjectId
from openai import OpenAI

#! Initialize ---------------------------------------------------------------
config = UltraConfig('config.json')
log = logger('agents_log', 
            filename='debug/agents.log', 
            include_extra_info=config.get("logging.include_extra_info", False), 
            write_to_file=config.get("logging.write_to_file", False), 
            log_level=config.get("logging.development_level", "DEBUG") if environment == 'development' else config.get("logging.production_level", "INFO"))

# Initialize OpenAI client
openai_client = OpenAI(api_key=openai_api_key)

#! Agent functions ---------------------------------------------------------
def create_agent(name,
                role="",
                capabilities=[],
                rules=[],
                model_provider="openai",
                model="gpt-4o",
                max_history=20,
                tools=[],
                user_id=None):
    """Create new agent with associated Chroma collection"""

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

    collection_name = str(ObjectId())
    # Create Chroma collection
    chroma_client.create_collection(collection_name)
    
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
        "chroma_collection": collection_name,
        "files": [],
        "created_at": datetime.now(),
        "system_agent": False
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
        
    # Prevent deletion of system agents
    if agent.get("system_agent", False):
        raise PermissionError("Cannot delete system agents")
    
    # Delete Chroma collection
    chroma_client.delete_collection(agent["chroma_collection"])
    
    # Delete all associated files
    db.files.delete_many({"agent_id": ObjectId(agent_id)})
    
    # Delete agent record
    db.agents.delete_one({"_id": ObjectId(agent_id)})