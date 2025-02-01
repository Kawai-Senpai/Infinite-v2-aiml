import boto3
import os
import time
import uuid
import glob
import psutil
import time
from functools import wraps
from ultraconfiguration import UltraConfig
from ultraprint.logging import logger
from keys.keys import aws_access_key_id, aws_secret , environment

#! Initialize ---------------------------------------------------------------
config = UltraConfig('config.json')
log = logger('s3_loader_log', 
            filename='debug/s3_loader.log', 
            include_extra_info=config.get("logging.include_extra_info", False), 
            write_to_file=config.get("logging.write_to_file", False), 
            log_level=config.get("logging.development_level", "DEBUG") if environment == 'development' else config.get("logging.production_level", "INFO"))

# essential variables
temp_dir = config.get("caching.dir", "cache")
aws_region = config.get("aws.region", "us-east-1")
default_bucket_name = config.get("aws.default_bucket_name", "infinite-bucket")

# Ensure Temp directory exists
os.makedirs(temp_dir, exist_ok=True)

def generate_unique_filename(original_filename):
    """Generate a unique filename using timestamp and UUID"""
    timestamp = int(time.time())
    unique_id = str(uuid.uuid4())[:8]
    extension = os.path.splitext(original_filename)[1]
    return f"{timestamp}_{unique_id}{extension}"

def get_unique_filename():
    """Generate a unique filename using timestamp and UUID"""
    timestamp = int(time.time())
    unique_id = str(uuid.uuid4())[:8]
    return f"{timestamp}_{unique_id}"

def retry_on_file_access_error(max_attempts=3, delay=1):
    """Decorator to retry operations on file access error"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except PermissionError as e:
                    attempts += 1
                    if attempts == max_attempts:
                        raise
                    log.warning(f"File access error, attempt {attempts}/{max_attempts}. Retrying in {delay} seconds...")
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

def force_close_file_handles(file_path):
    """Force close any open handles to the specified file"""
    try:
        for proc in psutil.process_iter():
            try:
                for item in proc.open_files():
                    if file_path in item.path:
                        proc.kill()
                        log.warning(f"Forced close of process using file: {file_path}")
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
    except Exception as e:
        log.error(f"Error while trying to force close file handles: {str(e)}")

@retry_on_file_access_error(max_attempts=3, delay=1)
def cleanup_cache(file_path=None):
    """
    Clean up files in cache directory with retry mechanism.
    If file_path is provided, delete specific file, else delete all files.
    """
    try:
        if file_path:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except PermissionError:
                    force_close_file_handles(file_path)
                    os.remove(file_path)
                log.success(f"Deleted file {file_path}")
            else:
                log.warning(f"File {file_path} not found, skipping deletion")
        else:
            files = glob.glob(os.path.join(temp_dir, "*"))
            for f in files:
                try:
                    os.remove(f)
                except PermissionError:
                    force_close_file_handles(f)
                    os.remove(f)
            log.success(f"Deleted all files in cache directory")
    except Exception as e:
        log.error(f"Error during cleanup: {str(e)}")
        raise

def download_from_s3(key, unique_filename=False, bucket_name=default_bucket_name):
    """
    Downloads a file directly from S3 to cache directory.
    Returns the local file path.
    """
    if unique_filename:
        name = generate_unique_filename(key)
    else:
        name = key.split("/")[-1]
        
    local_path = os.path.join(temp_dir, name)
    session = boto3.Session( 
        aws_access_key_id=aws_access_key_id, 
        aws_secret_access_key=aws_secret, 
        region_name=aws_region 
        )
    s3 = session.client("s3", region_name=aws_region)
    s3.download_file(bucket_name, key, local_path)
    log.success(f"Downloaded {key} from S3 bucket {bucket_name} to {local_path}")
    return local_path

def upload_to_s3(key, local_path, bucket_name=default_bucket_name):
    """
    Uploads a file directly to S3 from the local path.
    Returns the S3 key.
    """
    if not os.path.exists(local_path):
        raise FileNotFoundError(f"Local file {local_path} not found")
    
    session = boto3.Session( 
        aws_access_key_id=aws_access_key_id, 
        aws_secret_access_key=aws_secret, 
        region_name=aws_region 
        )
    s3 = session.client("s3", region_name=aws_region)
    s3.upload_file(local_path, bucket_name, key)
    log.success(f"Uploaded {local_path} to S3 bucket {bucket_name} as {key}")
    
    return key

def list_files_in_s3_directory(directory, only_files=True, recursive=False, bucket_name=default_bucket_name):
    """
    List all files in a specific S3 directory.
    If only_files is True, ignore any subdirectories.
    If recursive is False, do not go into subdirectories.
    """
    session = boto3.Session( 
        aws_access_key_id=aws_access_key_id, 
        aws_secret_access_key=aws_secret, 
        region_name=aws_region 
        )
    s3 = session.client("s3", region_name=aws_region)
    response = s3.list_objects_v2(Bucket=bucket_name, Prefix=directory)
    
    if 'Contents' not in response:
        return []
    
    if only_files:
        if recursive:
            files = [item['Key'] for item in response['Contents'] if not item['Key'].endswith('/') and item['Key'] != directory]
        else:
            files = [item['Key'] for item in response['Contents'] if not item['Key'].endswith('/') and item['Key'] != directory and '/' not in item['Key'][len(directory):]]
    else:
        if recursive:
            files = [item['Key'] for item in response['Contents'] if item['Key'] != directory]
        else:
            files = [item['Key'] for item in response['Contents'] if item['Key'] != directory and '/' not in item['Key'][len(directory):]]
    
    log.success(f"Listed files in S3 directory {directory}")
    return files

def generate_download_link(key, expiration=3600, bucket_name=default_bucket_name):
    """
    Generate a pre-signed URL for downloading an S3 object.
    
    Args:
        key (str): The S3 object key
        expiration (int): Number of seconds until the URL expires (default: 1 hour)
        bucket_name (str): The S3 bucket name
    
    Returns:
        str: A pre-signed URL that can be used to download the object
    """
    session = boto3.Session( 
        aws_access_key_id=aws_access_key_id, 
        aws_secret_access_key=aws_secret, 
        region_name=aws_region 
    )
    s3 = session.client("s3", region_name=aws_region)
    
    try:
        url = s3.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket_name,
                'Key': key
            },
            ExpiresIn=expiration
        )
        log.success(f"Generated temporary download link for {key} (expires in {expiration} seconds)")
        return url
    except Exception as e:
        log.error(f"Error generating download link: {str(e)}")
        raise
