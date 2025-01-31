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
    collections = config.get("chroma.structure", [])
    for collection in collections:
        if collection not in [col.name for col in client.list_collections()]:
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

def insert_documents(collection_name, documents, metadatas=None, ids=None):
    """Insert document(s) into specified ChromaDB collection"""
    try:
        # Get the collection
        collection = client.get_collection(collection_name)
        
        # Handle single document vs list of documents
        if isinstance(documents, str):
            documents = [documents]
            metadatas = [metadatas] if metadatas else [{}]
            ids = [ids] if ids else [str(ObjectId())]
        else:
            # If no metadata provided, create empty dicts
            metadatas = metadatas if metadatas else [{} for _ in documents]
            # If no ids provided, generate ObjectIds
            ids = ids if ids else [str(ObjectId()) for _ in documents]
        
        # Generate embeddings
        embeddings = embed(documents)
        if embeddings is None:
            raise ValueError("Failed to generate embeddings")
        
        # Insert into collection
        collection.add(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        log.success(f"Successfully inserted {len(documents)} document(s) into {collection_name}")
        return True, ids
        
    except Exception as e:
        log.error(f"Error inserting document(s) into {collection_name}: {str(e)}")
        return False, None

def search_documents(collection_name, query, n_results=5, similarity_threshold=0.7):
    """
    Search for similar documents in the specified collection
    Args:
        collection_name (str): Name of the collection to search in
        query (str or list): Query text or list of queries
        n_results (int): Number of results to return per query
        similarity_threshold (float): Minimum similarity score (0-1) to include in results
    Returns:
        list: List of dictionaries containing search results
    """
    try:
        collection = client.get_collection(collection_name)
        
        # Handle single query vs multiple queries
        if isinstance(query, str):
            queries = [query]
        else:
            queries = query
            
        # Generate embeddings for queries
        query_embeddings = embed(queries)
        if query_embeddings is None:
            raise ValueError("Failed to generate query embeddings")
        
        # Convert to list if single query
        if isinstance(query_embeddings[0], float):
            query_embeddings = [query_embeddings]
            
        all_results = []
        
        # Process each query
        for q, q_embedding in zip(queries, query_embeddings):
            result = collection.query(
                query_embeddings=q_embedding,
                n_results=n_results,
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
        log.error(f"Error searching documents in {collection_name}: {str(e)}")
        return None
