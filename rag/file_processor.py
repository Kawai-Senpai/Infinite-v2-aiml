from keys.keys import environment
from ultraconfiguration import UltraConfig
from ultraprint.logging import logger

#! Initialize ---------------------------------------------------------------
config = UltraConfig('config.json')
log = logger('file_processor_log', 
            filename='debug/file_processor.log', 
            include_extra_info=config.get("logging.include_extra_info", False), 
            write_to_file=config.get("logging.write_to_file", False), 
            log_level=config.get("logging.development_level", "DEBUG") if environment == 'development' else config.get("logging.production_level", "INFO"))

#! Chunking functions --------------------------------------------------------
def sentence_chunker(text, chunk_size=3, overlap=1):
    """Split text into sentence-level chunks."""
    log.debug(f"Starting sentence chunking with size={chunk_size}, overlap={overlap}")
    log.debug(f"Input text length: {len(text)} characters")
    
    sentences = [s.strip() for s in text.split('.') if s.strip()]
    log.debug(f"Found {len(sentences)} sentences")
    
    chunks = set()
    i = 0
    while i < len(sentences):
        chunk = '. '.join(sentences[i : i + chunk_size])
        chunks.add(chunk)
        i += (chunk_size - overlap)
    
    result = list(filter(None, chunks))
    log.success(f"Created {len(result)} sentence chunks")
    return result

def character_chunker(text, chunk_size=500, overlap=100):
    log.debug(f"Starting character chunking with size={chunk_size}, overlap={overlap}")
    log.debug(f"Input text length: {len(text)} characters")
    
    chunks = set()
    start = 0
    end = chunk_size
    while start < len(text):
        chunk = text[start:end]
        if chunk.strip():
            chunks.add(chunk)
        start += (chunk_size - overlap)
        end += (chunk_size - overlap)
    
    result = list(chunks)
    log.success(f"Created {len(result)} character chunks")
    return result

