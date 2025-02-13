from database.mongo import client as mongo_client
from keys.keys import environment
from ultraconfiguration import UltraConfig
from ultraprint.logging import logger
from datetime import datetime, timezone
from bson import ObjectId
from database.chroma import delete_agent_documents
import importlib  # added for dynamic tool import
import importlib.util
from pathlib import Path
import os
from utilities.save_json import convert_objectid_to_str

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
                user_id: str = None,
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
    
    # Validate tools dynamically
    for tool in tools:
        try:
            importlib.import_module(f"tools.{tool}.main")
        except ImportError as e:
            raise ValueError(f"Invalid tool: {tool}") from e

    # Validate number of collections
    if not 1 <= num_collections <= config.get("constraints.max_num_collections", 4):
        raise ValueError("Number of collections must be between 1 and 4")

    # Validate memory size
    if not isinstance(max_memory_size, int) or not 1 <= max_memory_size <= config.get("constraints.max_memory_size", 10):
        raise ValueError("max_memory_size must be an integer between 1 and 15")

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
        "max_memory_size": max_memory_size, 
        "created_at": datetime.now(timezone.utc),
        "agent_type": agent_type  # Replace system_agent with agent_type
    }
    
    if user_id:
        agent_data["user_id"] = str(user_id)  # Store as string
    
    # Updated: insert directly into the agents collection
    agent = db.insert_one(agent_data)
    return agent.inserted_id

def delete_agent(agent_id, user_id=None):
    """Completely remove an agent and its data; if user_id is given, only allow deletion if it matches."""
    db = mongo_client.ai
    agent = db.agents.find_one({"_id": ObjectId(agent_id)})
    
    if not agent:
        raise ValueError("Agent not found")
    
    if user_id and ("user_id" not in agent or agent["user_id"] != user_id):  # Direct string comparison
        raise ValueError("Not authorized to delete this agent")
    
    # Delete all documents from Chroma
    delete_agent_documents(agent_id)
    
    # Delete all associated files
    db.files.delete_many({"agent_id": ObjectId(agent_id)})
    
    # Delete agent record
    db.agents.delete_one({"_id": ObjectId(agent_id)})

def get_all_agents_for_user(user_id: str, limit=20, skip=0, sort_by="created_at", sort_order=-1):
    """Return paginated and sorted list of agents that belong to a specific user."""
    db = mongo_client.ai
    agents = list(db.agents.find({"user_id": str(user_id)}).sort(sort_by, sort_order).skip(skip).limit(limit))
    for agent in agents:
        agent["_id"] = convert_objectid_to_str(agent["_id"])
        if "created_at" in agent:
            agent["created_at"] = agent["created_at"].isoformat() if hasattr(agent["created_at"], "isoformat") else convert_objectid_to_str(agent["created_at"])
        if "updated_at" in agent:
            agent["updated_at"] = agent["updated_at"].isoformat() if hasattr(agent["updated_at"], "isoformat") else convert_objectid_to_str(agent["updated_at"])
        if "files" in agent:  # Added conversion for files list
            agent["files"] = [convert_objectid_to_str(f) for f in agent["files"]]
    return agents

def get_all_nonprivate_agents_for_user(user_id: str, limit=20, skip=0, sort_by="created_at", sort_order=-1):
    """Return paginated and sorted list of agents that belong to a specific user, excluding private agents."""
    db = mongo_client.ai
    agents = list(db.agents.find({"user_id": str(user_id), "agent_type": {"$ne": "private"}})
                .sort(sort_by, sort_order)
                .skip(skip)
                .limit(limit))
    for agent in agents:
        agent["_id"] = convert_objectid_to_str(agent["_id"])
        if "created_at" in agent:
            agent["created_at"] = agent["created_at"].isoformat() if hasattr(agent["created_at"], "isoformat") else convert_objectid_to_str(agent["created_at"])
        if "updated_at" in agent:
            agent["updated_at"] = agent["updated_at"].isoformat() if hasattr(agent["updated_at"], "isoformat") else convert_objectid_to_str(agent["updated_at"])
        if "files" in agent:  # Added conversion for files list
            agent["files"] = [convert_objectid_to_str(f) for f in agent["files"]]
    return agents

def get_all_public_agents(limit=20, skip=0, sort_by="created_at", sort_order=-1):
    """Return paginated and sorted list of public agents."""
    db = mongo_client.ai
    agents = list(db.agents.find({"agent_type": "public"})
                .sort(sort_by, sort_order)
                .skip(skip)
                .limit(limit))
    for agent in agents:
        agent["_id"] = convert_objectid_to_str(agent["_id"])
        if "created_at" in agent:
            agent["created_at"] = agent["created_at"].isoformat() if hasattr(agent["created_at"], "isoformat") else convert_objectid_to_str(agent["created_at"])
        if "updated_at" in agent:
            agent["updated_at"] = agent["updated_at"].isoformat() if hasattr(agent["updated_at"], "isoformat") else convert_objectid_to_str(agent["updated_at"])
        if "files" in agent:
            agent["files"] = [convert_objectid_to_str(f) for f in agent["files"]]
    return agents

def get_all_approved_agents(limit=20, skip=0, sort_by="created_at", sort_order=-1):
    """Return paginated and sorted list of approved agents."""
    db = mongo_client.ai
    agents = list(db.agents.find({"agent_type": "approved"})
                .sort(sort_by, sort_order)
                .skip(skip)
                .limit(limit))
    for agent in agents:
        agent["_id"] = convert_objectid_to_str(agent["_id"])
        if "created_at" in agent:
            agent["created_at"] = agent["created_at"].isoformat() if hasattr(agent["created_at"], "isoformat") else convert_objectid_to_str(agent["created_at"])
        if "updated_at" in agent:
            agent["updated_at"] = agent["updated_at"].isoformat() if hasattr(agent["updated_at"], "isoformat") else convert_objectid_to_str(agent["updated_at"])
        if "files" in agent:
            agent["files"] = [convert_objectid_to_str(f) for f in agent["files"]]
    return agents

def get_all_system_agents(limit=20, skip=0, sort_by="created_at", sort_order=-1):
    """Return paginated and sorted list of system agents."""
    db = mongo_client.ai
    agents = list(db.agents.find({"agent_type": "system"})
                .sort(sort_by, sort_order)
                .skip(skip)
                .limit(limit))
    for agent in agents:
        agent["_id"] = convert_objectid_to_str(agent["_id"])
        if "created_at" in agent:
            agent["created_at"] = agent["created_at"].isoformat() if hasattr(agent["created_at"], "isoformat") else convert_objectid_to_str(agent["created_at"])
        if "updated_at" in agent:
            agent["updated_at"] = agent["updated_at"].isoformat() if hasattr(agent["updated_at"], "isoformat") else convert_objectid_to_str(agent["updated_at"])
        if "files" in agent:
            agent["files"] = [convert_objectid_to_str(f) for f in agent["files"]]
    return agents

def get_agent(agent_id, user_id=None):
    """Return details of a single agent by agent_id; if user_id is given, restrict access to agents owned by that user."""
    db = mongo_client.ai.agents
    agent = db.find_one({"_id": ObjectId(agent_id)})
    if not agent:
        raise ValueError("Agent not found")
    if user_id and ("user_id" in agent and agent["user_id"] != user_id):  # Direct string comparison
        raise ValueError("Not authorized to view this agent")
    agent["_id"] = convert_objectid_to_str(agent["_id"])
    if "created_at" in agent:
        agent["created_at"] = agent["created_at"].isoformat() if hasattr(agent["created_at"], "isoformat") else convert_objectid_to_str(agent["created_at"])
    if "updated_at" in agent:
        agent["updated_at"] = agent["updated_at"].isoformat() if hasattr(agent["updated_at"], "isoformat") else convert_objectid_to_str(agent["updated_at"])
    # Convert files ObjectId to string
    if "files" in agent:
        agent["files"] = [convert_objectid_to_str(file) for file in agent["files"]]
    return agent

def get_available_tools():
    """Return a list of all available tools and their metadata"""
    available_tools = []
    
    # Get the directory where the tools package is located
    tools_dir = Path(os.path.dirname(__file__)).parent / "tools"
    
    # Check each directory in the tools folder
    try:
        for tool_path in tools_dir.iterdir():
            if not tool_path.is_dir() or tool_path.name.startswith('__'):
                continue
                
            try:
                tool_name = tool_path.name
                
                # Try to import the tool's main module
                tool_module = importlib.import_module(f"tools.{tool_name}.main")
                
                # Get tool metadata with default values
                tool_info = {
                    "name": tool_name,
                    "description": getattr(tool_module, "_info", ""),
                    "author": getattr(tool_module, "_author", "Unknown"),
                    "group": getattr(tool_module, "_group", ""),
                    "type": getattr(tool_module, "_type", "thirdparty")  # default to thirdparty if not specified
                }

                # Validate tool type
                if tool_info["type"] not in ["official", "thirdparty"]:
                    tool_info["type"] = "thirdparty"  # fallback to thirdparty if invalid type
                
                available_tools.append(tool_info)
                
            except ImportError as e:
                log.warning(f"Could not import tool {tool_name}: {str(e)}")
                continue
                
    except Exception as e:
        log.error(f"Error scanning tools directory: {str(e)}")
        raise ValueError("Could not fetch available tools")

    return available_tools

def update_agent(agent_id, user_id=None, **updates):
    """Update an agent's details"""
    db = mongo_client.ai.agents
    agent = db.find_one({"_id": ObjectId(agent_id)})
    
    if not agent:
        raise ValueError("Agent not found")
    
    if user_id and ("user_id" not in agent or agent["user_id"] != user_id):
        raise ValueError("Not authorized to update this agent")

    if "user_id" in updates:
        del updates["user_id"]  # Remove or rename to avoid conflict

    # Fields that can be updated
    allowed_updates = {
        "name", "role", "capabilities", "rules", "agent_type"
    }

    # Filter out any updates that aren't in allowed_updates
    valid_updates = {k: v for k, v in updates.items() if k in allowed_updates}

    if "agent_type" in valid_updates:
        # Validate agent type
        valid_agent_types = ["system", "public", "approved", "private"]
        if valid_updates["agent_type"] not in valid_agent_types:
            raise ValueError("Invalid agent type. Must be one of: system, public, approved, private")

    # Add updated_at timestamp
    valid_updates["updated_at"] = datetime.now(timezone.utc)

    # Update the agent
    result = db.update_one(
        {"_id": ObjectId(agent_id)},
        {"$set": valid_updates}
    )

    if result.modified_count == 0:
        raise ValueError("No changes were made to the agent")

    return True
