from pymongo import MongoClient
from keys.keys import mongo_uri, environment
from ultraprint.logging import logger
from ultraconfiguration import UltraConfig

#! Initialize ---------------------------------------------------------------
config = UltraConfig('config.json')
log = logger('mongo_log', 
            filename='debug/mongo.log', 
            include_extra_info=config.get("logging.include_extra_info", False), 
            write_to_file=config.get("logging.write_to_file", False), 
            log_level=config.get("logging.development_level", "DEBUG") if environment == 'development' else config.get("logging.production_level", "INFO"))

# Create the mongo client
client = MongoClient(mongo_uri, 
                    tls=True, 
                    tlsAllowInvalidCertificates=True)

#! MongoDB functions ---------------------------------------------------------
#* Check if MongoDB connection is successful ---------------------------------
def pingtest():
    # Send a ping to confirm a successful connection
    try:
        client.admin.command('ping')
        return True
    except Exception as e:
        log.error(e)
        return False

#* Ensure required databases and collections exist ---------------------------
def database_exists(db_name):
    """Check if a database exists."""
    return db_name in client.list_database_names()

def collection_exists(db_name, collection_name):
    """Check if a collection exists in a database."""
    if not database_exists(db_name):
        return False
    return collection_name in client[db_name].list_collection_names()

def get_required_structure():
    """Get the required MongoDB structure."""
    return config.get("mongo.structure", {})

def init_db_structure():
    """Initialize all required databases and collections."""
    required_structure = get_required_structure()

    for db_name, collections in required_structure.items():
        # Create database by accessing it
        db = client[db_name]
        for collection_name in collections:
            if not collection_exists(db_name, collection_name):
                # Create collection by accessing it
                db.create_collection(collection_name)
                log.success(f"Created collection '{collection_name}' in database '{db_name}'")

def check_mongo_structure(verbose=True):
    """Comprehensive check of the MongoDB structure with verbose output."""
    if verbose:
        log.info("Checking MongoDB connection...")
    
    if not pingtest():
        log.error("MongoDB connection failed!")
        return False
    
    if verbose:
        log.success("MongoDB connection successful!")

    required_structure = get_required_structure()

    all_ok = True
    for db_name, collections in required_structure.items():
        if verbose:
            log.info(f"\nChecking database '{db_name}'...")
        
        if not database_exists(db_name):
            if verbose:
                log.error(f"Database '{db_name}' does not exist!")
            all_ok = False
            continue
        
        if verbose:
            log.success(f"Database '{db_name}' exists")
        
        for collection_name in collections:
            if verbose:
                log.info(f"Checking collection '{collection_name}'...")
            
            if not collection_exists(db_name, collection_name):
                if verbose:
                    log.error(f"Collection '{collection_name}' does not exist!")
                all_ok = False
                continue
            
            if verbose:
                log.success(f"Collection '{collection_name}' exists")

    return all_ok

