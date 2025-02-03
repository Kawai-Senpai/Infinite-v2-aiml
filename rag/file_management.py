from database.mongo import client as mongo_client
from database.chroma import insert_documents, delete_file_documents
from rag.file_processor import sentence_chunker, character_chunker
from keys.keys import environment
from ultraconfiguration import UltraConfig
from ultraprint.logging import logger
from datetime import datetime, timezone
from bson import ObjectId
import hashlib

#! Initialize ---------------------------------------------------------------
config = UltraConfig('config.json')
log = logger('file_management_log', 
            filename='debug/file_management.log', 
            include_extra_info=config.get("logging.include_extra_info", False), 
            write_to_file=config.get("logging.write_to_file", False), 
            log_level=config.get("logging.development_level", "DEBUG") if environment == 'development' else config.get("logging.production_level", "INFO"))

def add_file(agent_id, text, file_name, file_type, chunk_size=3, overlap=1, chunk_type="sentence", collection_id=None, origin=None):
    """Chunk text and store vector embeddings, no PDF loading."""
    log.info(f"Adding file '{file_name}' for agent {agent_id}")
    
    db = mongo_client.ai.agents
    agent = db.find_one({"_id": ObjectId(agent_id)})
    if not agent:
        log.error(f"Agent {agent_id} not found")
        raise ValueError("Agent not found")

    # Use first collection ID if none specified
    if not collection_id:
        collection_id = agent["collection_ids"][0]
    elif collection_id not in agent["collection_ids"]:
        raise ValueError("Invalid collection ID for this agent")

    # Validate and update origin if provided
    if origin is not None:
        if file_type is None:
            raise ValueError("file_type must be provided")
        supported_types = config.get("supported.file_types", [])
        if file_type not in supported_types:
            raise ValueError(f"Unsupported file_type. Supported types: {supported_types}")
        origin["type"] = file_type
    else:
        origin = {"type": file_type}

    # Chunk the text
    log.debug(f"Chunking text using {chunk_type} method with size {chunk_size} and overlap {overlap}")
    if chunk_type == "character":
        chunks = character_chunker(text, chunk_size, overlap)
    else:
        chunks = sentence_chunker(text, chunk_size, overlap)
    
    log.info(f"Created {len(chunks)} chunks from file")

    chunk_ids = []
    file_id = str(ObjectId())  # Generate file_id first
    
    for i, chunk in enumerate(chunks):
        chunk_id = str(ObjectId())
        log.debug(f"Processing chunk {i+1}/{len(chunks)} with ID {chunk_id}")
        insert_documents(
            agent_id=agent_id,
            collection_id=collection_id,
            documents=[chunk],
            additional_metadata=[{
                "file_name": file_name,
                "file_id": file_id,  # Add file_id to metadata
                "chunk_number": i + 1
            }]
        )
        chunk_ids.append(chunk_id)

    file_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
    log.debug(f"File hash: {file_hash}")
    
    files_collection = mongo_client.ai.files
    files_collection.insert_one({
        "agent_id": ObjectId(agent_id),
        "filename": file_name,
        "chunk_ids": chunk_ids,
        "file_hash": file_hash,
        "collection_id": collection_id,  # Added collection_id to file record
        "origin": origin,               # New field: stores the origin dict with type added
        "uploaded_at": datetime.now(timezone.utc)
    })
    
    log.success(f"Successfully added file '{file_name}' with {len(chunk_ids)} chunks")
    return len(chunk_ids)

def delete_file(agent_id, file_id):
    """Remove specific file and its chunks"""
    log.info(f"Deleting file {file_id} for agent {agent_id}")

    db = mongo_client.ai.files
    file_data = db.find_one({"_id": ObjectId(file_id)})
    if not file_data:
        log.error(f"File {file_id} not found")
        raise ValueError("File not found")
    
    # Delete from Chroma using centralized function
    delete_file_documents(agent_id, file_id)
    
    # Delete metadata
    db.delete_one({"_id": ObjectId(file_id)})
    log.success(f"Successfully deleted file {file_id} and its chunks")

def get_all_files_for_agent(agent_id):
    """Return all files for a given agent."""
    db = mongo_client.ai.files
    return list(db.find({"agent_id": ObjectId(agent_id)}))

def get_all_collections_for_agent(agent_id):
    """Return all collection IDs for a given agent."""
    db = mongo_client.ai.agents
    agent = db.find_one({"_id": ObjectId(agent_id)})
    return agent.get("collection_ids", []) if agent else []

def get_all_files_for_collection(agent_id, collection_id):
    """
    Return files associated with a specific collection ID by filtering with both agent_id and collection_id.
    """
    db_files = mongo_client.ai.files
    return list(db_files.find({
        "agent_id": ObjectId(agent_id),
        "collection_id": collection_id
    }))