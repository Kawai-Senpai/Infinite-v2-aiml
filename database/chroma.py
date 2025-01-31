import chromadb
from keys.keys import chroma_host, chroma_port, environment
from ultraconfiguration import UltraConfig
from ultraprint.logging import logger

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