from PyPDF2 import PdfReader
import docx
import pandas as pd
import requests
from bs4 import BeautifulSoup
from utilities.s3_loader import download_from_s3, cleanup_cache
from ultraconfiguration import UltraConfig
from ultraprint.logging import logger
from keys.keys import environment
from utilities.scraping import scrape_page

config = UltraConfig('config.json')
log = logger('file_handler_log', 
            filename='debug/file_handler.log', 
            include_extra_info=config.get("logging.include_extra_info", False), 
            write_to_file=config.get("logging.write_to_file", False), 
            log_level=config.get("logging.development_level", "DEBUG") if environment == 'development' else config.get("logging.production_level", "INFO"))

def extract_from_pdf(s3_key, bucket_name):
    """Extract text from PDF file stored in S3"""
    try:
        local_path = download_from_s3(s3_key, bucket_name=bucket_name, unique_filename=True)
        with open(local_path, 'rb') as file:
            reader = PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
        cleanup_cache(local_path)
        return text.strip()
    except Exception as e:
        log.error(f"Error extracting PDF text: {str(e)}")
        cleanup_cache(local_path)
        raise

def extract_from_docx(s3_key, bucket_name):
    """Extract text from DOCX file stored in S3"""
    try:
        local_path = download_from_s3(s3_key, bucket_name=bucket_name, unique_filename=True)
        doc = docx.Document(local_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        cleanup_cache(local_path)
        return text.strip()
    except Exception as e:
        log.error(f"Error extracting DOCX text: {str(e)}")
        cleanup_cache(local_path)
        raise

def extract_from_excel(s3_key, bucket_name):
    """Extract text from Excel file stored in S3"""
    try:
        local_path = download_from_s3(s3_key, bucket_name=bucket_name, unique_filename=True)
        df = pd.read_excel(local_path)
        text = df.to_string()
        cleanup_cache(local_path)
        return text.strip()
    except Exception as e:
        log.error(f"Error extracting Excel text: {str(e)}")
        cleanup_cache(local_path)
        raise

def extract_from_webpage(url):
    """Extract text from webpage"""
    try:
        return scrape_page(url)
    except Exception as e:
        log.error(f"Error extracting webpage text: {str(e)}")
        raise

def get_file_content(file_type, details):
    """Main function to extract text based on file type"""
    handlers = {
        "pdf": lambda d: extract_from_pdf(d["s3_key"], d["s3_bucket"]),
        "docx": lambda d: extract_from_docx(d["s3_key"], d["s3_bucket"]),
        "excel": lambda d: extract_from_excel(d["s3_key"], d["s3_bucket"]),
        "webpage": lambda d: extract_from_webpage(d["url"])
    }
    
    if file_type not in handlers:
        raise ValueError(f"Unsupported file type: {file_type}")
        
    return handlers[file_type](details)
