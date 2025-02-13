from multiprocessing import Process
from bson import ObjectId
from datetime import datetime, timezone
import hashlib
import traceback
from database.mongo import client as mongo_client
from rag.file_handler import get_file_content
from rag.file_management import add_file

def update_progress(job_id: str, step: str, status: str = "IN_PROGRESS", error: str = None, details: dict = None):
    """Update job progress in MongoDB with detailed step tracking."""
    status = status.upper()  # Enforce uppercase status
    step_data = {
        "status": status,
        "timestamp": datetime.now(timezone.utc)
    }
    if error:
        step_data["error"] = str(error)
    if details:
        step_data.update(details)
    update = {
        "details.current_step": step,
        f"details.steps.{step}": step_data
    }
    mongo_client.jobs.files.update_one({"_id": ObjectId(job_id)}, {"$set": update})

# Updated process_file_job to pass s3_bucket and s3_key directly
def process_file_job(job_id: str, agent_id: str, user_id: str,
                    file_name: str, file_type: str,
                    chunk_size: int, overlap: int, chunk_type: str,
                    s3_bucket: str = None, s3_key: str = None,
                    collection_index: int = None):
    """Background process for handling file processing using dedicated functions with step timing."""
    try:
        # Build details based on file type: if webpage, use s3_key as URL; else use bucket/key
        if file_type == "webpage":
            details = {"url": s3_key}
        else:
            details = {"s3_key": s3_key, "s3_bucket": s3_bucket}
        
        # Downloading step with timing
        update_progress(job_id, "downloading", details={"input": details})
        download_start = datetime.now(timezone.utc)
        text = get_file_content(file_type, details)
        download_duration = (datetime.now(timezone.utc) - download_start).total_seconds()
        update_progress(job_id, "downloading", status="COMPLETED", details={"duration": download_duration})
        
        # Chunking step with timing
        update_progress(job_id, "chunking")
        chunking_start = datetime.now(timezone.utc)
        # Pass s3_bucket and s3_key to add_file unconditionally
        chunks_added = add_file(agent_id, text, file_name, file_type,
                                chunk_size=chunk_size, overlap=overlap,
                                chunk_type=chunk_type, user_id=user_id,
                                s3_bucket=s3_bucket, s3_key=s3_key,
                                collection_index=collection_index)
        chunking_duration = (datetime.now(timezone.utc) - chunking_start).total_seconds()
        update_progress(job_id, "chunking", status="COMPLETED", details={"duration": chunking_duration})
        
        file_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
        update_progress(job_id, "completed", status="COMPLETED", details={
            "results": {
                "chunks_added": chunks_added,
                "file_hash": file_hash
            }
        })
        # NEW: Update overall job status
        mongo_client.jobs.files.update_one({"_id": ObjectId(job_id)}, {"$set": {"status": "COMPLETED"}})
        
    except Exception as e:
        error_msg = traceback.format_exc()  # Capture full traceback
        update_progress(job_id, "failed", status="FAILED", error=error_msg)
    
# Updated start_file_job signature with optional s3_bucket and s3_key
def start_file_job(agent_id: str, user_id: str, file_name: str, file_type: str,
                s3_bucket: str = None, s3_key: str = None,
                chunk_size: int = 3, overlap: int = 1, chunk_type: str = "sentence",
                collection_index: int = None) -> dict:
    """
    Start a file processing job.
    Immediately inserts a job record in 'jobs' collection with status 'IN_PROGRESS'
    and spawns a background process to process the file.
    """
    job_collection = mongo_client.jobs.files
    job_record = {
        "job_type": "file_upload",
        "agent_id": agent_id,
        "user_id": user_id,
        "file_name": file_name,
        "file_type": file_type,
        "status": "IN_PROGRESS",  # Updated to uppercase
        "created_at": datetime.now(timezone.utc),
        "details": {
            "current_step": None,
            "steps": {}
        }
    }
    # For webpage, store the URL instead of s3_bucket/s3_key
    if file_type == "webpage":
        job_record["url"] = s3_key
    else:
        job_record["s3_bucket"] = s3_bucket
        job_record["s3_key"] = s3_key

    result = job_collection.insert_one(job_record)
    job_id = str(result.inserted_id)
    
    # Spawn background process to process the file job
    Process(
        target=process_file_job,
        args=(job_id, agent_id, user_id, file_name, file_type, chunk_size, overlap, chunk_type, s3_bucket, s3_key, collection_index)
    ).start()
    
    return {"job_id": job_id}
