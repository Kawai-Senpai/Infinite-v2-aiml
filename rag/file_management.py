from database.mongo import client as mongo_client
from database.chroma import insert_documents, delete_file_documents
from rag.file_processor import sentence_chunker, character_chunker
from keys.keys import environment
from ultraconfiguration import UltraConfig
from ultraprint.logging import logger
from datetime import datetime, timezone
from bson import ObjectId
import hashlib

# Helper to convert a value to ObjectId if it's a string.
def to_obj(val):
    if isinstance(val, str) and ObjectId.is_valid(val):
        return ObjectId(val)
    return val

#! Initialize ---------------------------------------------------------------
config = UltraConfig('config.json')
log = logger('file_management_log', 
            filename='debug/file_management.log', 
            include_extra_info=config.get("logging.include_extra_info", False), 
            write_to_file=config.get("logging.write_to_file", False), 
            log_level=config.get("logging.development_level", "DEBUG") if environment == 'development' else config.get("logging.production_level", "INFO"))

def add_file(agent_id, text, file_name, file_type, chunk_size=3, overlap=1, chunk_type="sentence", 
             *,  # force subsequent params to be keyword-only
             collection_index: int = None, origin=None, user_id=None, s3_bucket=None, s3_key=None):
    """Chunk text and store vector embeddings using collection_index for bucket selection."""
    # Convert supplied IDs
    agent_id = to_obj(agent_id)
    if user_id:
        user_id = to_obj(user_id)
        
    log.info(f"Adding file '{file_name}' for agent {agent_id}")
    
    db = mongo_client.ai.agents
    agent = db.find_one({"_id": agent_id})
    if not agent:
        log.error(f"Agent {agent_id} not found")
        raise ValueError("Agent not found")
    if user_id:
        if "user_id" not in agent or str(agent["user_id"]) != str(user_id):
            raise ValueError("Not authorized to modify files for this agent")
            
    # Use collection_index to determine the target collection_id (default index 0)
    try:
        idx = collection_index if collection_index is not None else 0
        collection_id = agent["collection_ids"][idx]
    except IndexError:
        raise ValueError("Invalid collection index for this agent")
    
    if origin is not None:
        if file_type is None:
            raise ValueError("file_type must be provided")
        supported_types = config.get("supported.file_types", [])
        if file_type not in supported_types:
            raise ValueError(f"Unsupported file_type. Supported types: {supported_types}")
        origin["type"] = file_type
    else:
        origin = {"type": file_type}
    
    log.debug(f"Chunking text using {chunk_type} method with size {chunk_size} and overlap {overlap}")
    if chunk_type == "character":
        chunks = character_chunker(text, chunk_size, overlap)
    else:
        chunks = sentence_chunker(text, chunk_size, overlap)
    
    log.info(f"Created {len(chunks)} chunks from file")
    chunk_ids = []
    file_id = str(ObjectId())
    
    for i, chunk in enumerate(chunks):
        chunk_id = str(ObjectId())
        log.debug(f"Processing chunk {i+1}/{len(chunks)} with ID {chunk_id}")
        insert_documents(
            agent_id=str(agent_id),
            collection_id=collection_id,
            documents=[chunk],
            additional_metadata=[{
                "file_name": file_name,
                "file_id": file_id,
                "chunk_number": i + 1
            }]
        )
        chunk_ids.append(chunk_id)
    
    file_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
    log.debug(f"File hash: {file_hash}")
    
    files_collection = mongo_client.ai.files
    file_doc = {
        "agent_id": agent_id,
        "filename": file_name,
        "chunk_ids": chunk_ids,
        "file_hash": file_hash,
        "collection_id": collection_id,
        "origin": origin,
        "file_type": file_type,  # Always record file type
        "uploaded_at": datetime.now(timezone.utc)
    }
    if file_type == "webpage":
        file_doc["url"] = s3_key
    else:
        file_doc["s3_bucket"] = s3_bucket
        file_doc["s3_key"] = s3_key

    if user_id:
        file_doc["user_id"] = user_id
    
    result = files_collection.insert_one(file_doc)
    file_doc["_id"] = result.inserted_id
    mongo_client.ai.agents.update_one({"_id": agent_id}, {"$push": {"files": file_doc["_id"]}})
    
    log.success(f"Successfully added file '{file_name}' with {len(chunk_ids)} chunks")
    return len(chunk_ids)

def delete_file(agent_id, file_id, user_id=None):
    """Remove specific file and its chunks with security check."""
    # Convert supplied IDs
    agent_id = to_obj(agent_id)
    file_id_obj = to_obj(file_id)
    if user_id:
        user_id = to_obj(user_id)

    log.info(f"Deleting file {file_id} for agent {agent_id}")

    db_files = mongo_client.ai.files
    file_data = db_files.find_one({"_id": file_id_obj})
    if not file_data:
        log.error(f"File {file_id} not found")
        raise ValueError("File not found")
    
    db_agents = mongo_client.ai.agents
    agent = db_agents.find_one({"_id": agent_id})
    if not agent:
        log.error(f"Agent {agent_id} not found")
        raise ValueError("Agent not found")
    # NEW: User ID check
    if user_id:
        if "user_id" not in agent or str(agent["user_id"]) != str(user_id):
            raise ValueError("Not authorized to delete file for this agent")
    
    # Delete from Chroma using centralized function
    delete_file_documents(str(agent_id), file_id)  # Use string version if needed
    
    # Delete metadata
    db_files.delete_one({"_id": file_id_obj})
    # NEW: Remove file reference from the agent document
    db_agents.update_one({"_id": agent_id}, {"$pull": {"files": file_id_obj}})
    log.success(f"Successfully deleted file {file_id} and its chunks")

def get_all_files_for_agent(agent_id, user_id=None, limit=20, skip=0, sort_by="uploaded_at", sort_order=-1):
    """Return paginated and sorted list of files for a given agent with optional security check."""
    agent_id = to_obj(agent_id)
    if user_id:
        user_id = to_obj(user_id)
        agent = mongo_client.ai.agents.find_one({"_id": agent_id})
        if agent and "user_id" in agent and str(agent["user_id"]) != str(user_id):
            raise ValueError("Not authorized to view files for this agent")
    
    files = list(mongo_client.ai.files.find({"agent_id": agent_id})
                .sort(sort_by, sort_order)
                .skip(skip)
                .limit(limit))
    
    # Convert ObjectIds to strings
    for file in files:
        file['_id'] = str(file['_id'])
        file['agent_id'] = str(file['agent_id'])
        if 'user_id' in file:
            file['user_id'] = str(file['user_id'])
    
    return files

def get_all_collections_for_agent(agent_id, user_id=None):
    """Return all collection IDs for a given agent with optional security check."""
    agent_id = to_obj(agent_id)
    if user_id:
        user_id = to_obj(user_id)
    agent = mongo_client.ai.agents.find_one({"_id": agent_id})
    if not agent:
        return []
    if user_id and "user_id" in agent and str(agent["user_id"]) != str(user_id):
        raise ValueError("Not authorized to view collections for this agent")
    return agent.get("collection_ids", [])

def get_all_files_for_collection(agent_id, collection_index: int, user_id=None, limit=20, skip=0, sort_by="uploaded_at", sort_order=-1):
    """Return paginated and sorted list of files for a specific collection using collection_index."""
    agent_id = to_obj(agent_id)
    db_agents = mongo_client.ai.agents
    agent = db_agents.find_one({"_id": agent_id})
    if not agent:
        raise ValueError("Agent not found")
    try:
        target_collection_id = agent["collection_ids"][collection_index]
    except IndexError:
        raise ValueError("Invalid collection index for this agent")
    
    if user_id:
        user_id = to_obj(user_id)
        if "user_id" in agent and str(agent["user_id"]) != str(user_id):
            raise ValueError("Not authorized to view files for this collection")
    
    files = list(mongo_client.ai.files.find({
        "agent_id": agent_id,
        "collection_id": target_collection_id
    }).sort(sort_by, sort_order)
      .skip(skip)
      .limit(limit))
    
    for file in files:
        file['_id'] = str(file['_id'])
        file['agent_id'] = str(file['agent_id'])
        if 'user_id' in file:
            file['user_id'] = str(file['user_id'])
    
    return files