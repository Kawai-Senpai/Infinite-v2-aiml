import chromadb
from bson import ObjectId
from keys.keys import chroma_host, chroma_port, environment, openai_api_key
from ultraconfiguration import UltraConfig
from ultraprint.logging import logger
from openai import OpenAI

#! Initialize ---------------------------------------------------------------
config = UltraConfig('config.json')
log = logger('chroma_log', 
            filename='debug/chroma.log', 
            include_extra_info=config.get("logging.include_extra_info", False), 
            write_to_file=config.get("logging.write_to_file", False), 
            log_level=config.get("logging.development_level", "DEBUG") if environment == 'development' else config.get("logging.production_level", "INFO"))

# Create the chroma client
client = chromadb.HttpClient(
    host=chroma_host,
    port=chroma_port)

# Initialize OpenAI client
openai_client = OpenAI(api_key=openai_api_key)

#! ChromaDB functions ---------------------------------------------------------
#* Check if ChromaDB connection is successful ---------------------------------
def pingtest():
    # Send a ping to confirm a successful connection
    try:
        client.list_collections()
        return True
    except Exception as e:
        print(e)
        return False

#* Ensure required collections exist ------------------------------------------
def create_collections():
    """Create shared documents collection if it doesn't exist"""
    all_collections = [col for col in config.get("chroma.structure", [])]
    # Updated: client.list_collections() now returns a list of names
    chroma_collections = client.list_collections()
    log.info(f"Existing collections: {chroma_collections}")
    for collection in all_collections:
        if collection not in chroma_collections:
            log.success(f"Creating collection: {collection}")
            client.create_collection(collection)

#! Embedding Insertion & Querying ---------------------------------------------
def embed(texts):
    """Generate embeddings for single or multiple texts using OpenAI's API"""
    try:
        # Convert single string to list for consistent handling
        if isinstance(texts, str):
            texts = [texts]
            
        response = openai_client.embeddings.create(
            input=texts,
            model=config.get("models.embedding", "text-embedding-3-small")
        )
        
        # Return single embedding if input was single string
        if len(texts) == 1:
            return response.data[0].embedding
        # Return list of embeddings for multiple inputs
        return [item.embedding for item in response.data]
    except Exception as e:
        log.error(f"Error generating embeddings: {str(e)}")
        return None

def insert_documents(agent_id, collection_id, documents, user_id=None, additional_metadata=None):
    """Insert document(s) into shared collection with agent and collection identifiers"""
    try:
        collection = client.get_collection("documents")
        
        # Handle single document vs list of documents
        if isinstance(documents, str):
            documents = [documents]
            additional_metadata = [additional_metadata] if additional_metadata else [{}]
            ids = [str(ObjectId())]
        else:
            additional_metadata = additional_metadata if additional_metadata else [{} for _ in documents]
            ids = [str(ObjectId()) for _ in documents]
        
        # Generate embeddings
        embeddings = embed(documents)
        if embeddings is None:
            raise ValueError("Failed to generate embeddings")
        
        # Prepare metadata
        metadatas = []
        for meta in additional_metadata:
            metadata = {
                "agent_id": str(agent_id),
                "collection_id": collection_id
            }
            if user_id:
                metadata["user_id"] = str(user_id)
            metadata.update(meta)
            metadatas.append(metadata)
        
        # Insert into collection
        collection.add(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        log.success(f"Inserted {len(documents)} document(s) into collection")
        return True, ids
    except Exception as e:
        log.error(f"Error inserting document(s): {str(e)}")
        return False, None

def search_documents(agent_id, collection_id, query, n_results=5, similarity_threshold=config.get("chroma.threshold", 0.5)):
    """Search for similar documents in the shared collection filtered by agent and collection IDs"""
    try:
        collection = client.get_collection("documents")
        
        # Handle single query vs multiple queries
        if isinstance(query, str):
            queries = [query]
        else:
            queries = query
            
        # Generate embeddings for queries
        query_embeddings = embed(queries)
        if query_embeddings is None:
            raise ValueError("Failed to generate query embeddings")
        
        if isinstance(query_embeddings[0], float):
            query_embeddings = [query_embeddings]
            
        all_results = []
        
        # Process each query with metadata filtering
        for q, q_embedding in zip(queries, query_embeddings):
            result = collection.query(
                query_embeddings=q_embedding,
                n_results=n_results,
                where={"$and": [{"agent_id": str(agent_id)}, {"collection_id": collection_id}]},
                include=['metadatas', 'documents', 'distances']
            )
            
            filtered_matches = []
            if not result or "metadatas" not in result or not result["metadatas"]:
                all_results.append({"query": q, "matches": []})
                continue
            
            # Process and filter results
            for doc, metadata, distance in zip(
                result["documents"][0], 
                result["metadatas"][0], 
                result["distances"][0]
            ):
                if metadata is None:
                    continue
                    
                similarity = 1 - (distance / 2)
                
                if similarity >= similarity_threshold:
                    filtered_matches.append({
                        "document": doc,
                        "metadata": metadata,
                        "similarity": round(similarity, 3)
                    })
            
            all_results.append({
                "query": q,
                "matches": sorted(filtered_matches, key=lambda x: x["similarity"], reverse=True)
            })
        
        # Return single result if single query
        if isinstance(query, str):
            return all_results[0]
        return all_results
        
    except Exception as e:
        log.error(f"Error searching documents in collection: {str(e)}")
        return None

def delete_agent_documents(agent_id):
    """Delete all documents associated with an agent"""
    try:
        collection = client.get_collection("documents")
        collection.delete(where={"agent_id": str(agent_id)})
        log.success(f"Deleted all documents for agent {agent_id}")
        return True
    except Exception as e:
        log.error(f"Error deleting agent documents: {str(e)}")
        return False

def delete_file_documents(agent_id, file_id):
    """Delete all documents associated with a specific file"""
    try:
        collection = client.get_collection("documents")
        collection.delete(where={
            "agent_id": str(agent_id),
            "file_id": str(file_id)
        })
        log.success(f"Deleted documents for file {file_id}")
        return True
    except Exception as e:
        log.error(f"Error deleting file documents: {str(e)}")
        return False

def delete_collection_documents(agent_id, collection_id):
    """Delete all documents in a specific collection"""
    try:
        collection = client.get_collection("documents")
        collection.delete(where={
            "agent_id": str(agent_id),
            "collection_id": collection_id
        })
        log.success(f"Deleted documents for collection {collection_id}")
        return True
    except Exception as e:
        log.error(f"Error deleting collection documents: {str(e)}")
        return False
