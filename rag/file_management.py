from database.mongo import client as mongo_client
from database.chroma import client as chroma_client, insert_documents
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

def add_file(agent_id, text, file_name, chunk_size=3, overlap=1, chunk_type="sentence"):
    """Chunk text and store vector embeddings, no PDF loading."""
    log.info(f"Adding file '{file_name}' for agent {agent_id}")
    
    db = mongo_client.ai.agents
    agent = db.find_one({"_id": ObjectId(agent_id)})
    if not agent:
        log.error(f"Agent {agent_id} not found")
        raise ValueError("Agent not found")

    # Chunk the text
    log.debug(f"Chunking text using {chunk_type} method with size {chunk_size} and overlap {overlap}")
    if chunk_type == "character":
        chunks = character_chunker(text, chunk_size, overlap)
    else:
        chunks = sentence_chunker(text, chunk_size, overlap)
    
    log.info(f"Created {len(chunks)} chunks from file")

    chunk_ids = []
    for i, chunk in enumerate(chunks):
        chunk_id = str(ObjectId())
        log.debug(f"Processing chunk {i+1}/{len(chunks)} with ID {chunk_id}")
        insert_documents(
            collection_name=agent["chroma_collection"],
            documents=[chunk],
            metadatas=[{"file_name": file_name}],
            ids=[chunk_id]
        )
        chunk_ids.append(chunk_id)

    file_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
    log.debug(f"File hash: {file_hash}")
    
    db.files.insert_one({
        "agent_id": ObjectId(agent_id),
        "filename": file_name,
        "chunk_ids": chunk_ids,
        "file_hash": file_hash,
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
    
    # Delete from Chroma
    agent = db.find_one({"_id": ObjectId(agent_id)})
    if not agent:
        log.error(f"Agent {agent_id} not found")
        raise ValueError("Agent not found")

    log.debug(f"Deleting {len(file_data['chunk_ids'])} chunks from Chroma")
    collection = chroma_client.get_collection(agent["chroma_collection"])
    collection.delete(ids=file_data["chunk_ids"])
    
    # Delete metadata
    db.delete_one({"_id": ObjectId(file_id)})
    log.success(f"Successfully deleted file {file_id} and its chunks")