from fastapi import APIRouter, HTTPException, Request
from rag.rag import start_file_job
from database.mongo import client as mongo_client
from bson import ObjectId
from utilities.save_json import convert_objectid_to_str
from errors.error_logger import log_exception_with_request
from rag.file_management import delete_file, get_all_files_for_agent, get_all_collections_for_agent, get_all_files_for_collection

router = APIRouter()

@router.post("/jobs/start")
async def start_job(
    request: Request,
    agent_id: str,
    file_name: str,
    file_type: str,
    user_id: str = None,  # made optional
    collection_index: int = None,  # new optional parameter to select a bucket
    s3_bucket: str = "infinite-v2-data",       
    s3_key: str = None,       
    chunk_size: int = 3,
    overlap: int = 1,
    chunk_type: str = "sentence"
):
    """Start a file processing job."""
    try:
        job_data = start_file_job(
            agent_id=agent_id,
            user_id=user_id,
            file_name=file_name,
            file_type=file_type,
            collection_index=collection_index,
            s3_bucket=s3_bucket,
            s3_key=s3_key,
            chunk_size=chunk_size,
            overlap=overlap,
            chunk_type=chunk_type
        )
        return {
            "message": "File processing job started successfully.",
            "job_id": job_data["job_id"]
        }
    except Exception as e:
        log_exception_with_request(e, start_job, request)
        raise HTTPException(status_code=500, detail={
            "message": "Failed to start file processing job.",
            "error": str(e)
        })

@router.get("/jobs/get/{job_id}")
async def get_job(job_id: str, request: Request):
    """Retrieve job details by job ID."""
    try:
        job_collection = mongo_client.jobs.files
        job = job_collection.find_one({"_id": ObjectId(job_id)})
        if job:
            job["_id"] = convert_objectid_to_str(job["_id"])
            return {
                "message": "Job details retrieved successfully.",
                "data": job
            }
        else:
            raise HTTPException(status_code=404, detail={
                "message": "Job not found.",
                "job_id": job_id
            })
    except Exception as e:
        log_exception_with_request(e, get_job, request)
        raise HTTPException(status_code=500, detail={
            "message": "Failed to retrieve job details.",
            "error": str(e)
        })

@router.delete("/{agent_id}/{file_id}")
async def delete_file_endpoint(agent_id: str, file_id: str, request: Request, user_id: str = None):
    try:
        delete_file(agent_id, file_id, user_id)
        return {"message": "File deleted successfully"}
    except Exception as e:
        log_exception_with_request(e, delete_file_endpoint, request)
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/files/all/{agent_id}")
async def retrieve_all_files_for_agent(agent_id: str, request: Request, user_id: str = None, limit: int = 20, skip: int = 0):
    """Return paginated list of all files for an agent."""
    try:
        data = get_all_files_for_agent(agent_id, user_id=user_id, limit=limit, skip=skip)
        return {"message": "Files retrieved successfully.", "data": data}
    except Exception as e:
        log_exception_with_request(e, retrieve_all_files_for_agent, request)
        raise HTTPException(status_code=500, detail={
            "message": "Failed to retrieve files.",
            "error": str(e)
        })

@router.get("/collections/all/{agent_id}")
async def retrieve_all_collections_for_agent(agent_id: str, request: Request, user_id: str = None):
    """Return all collection IDs for an agent."""
    try:
        collections = get_all_collections_for_agent(agent_id, user_id=user_id)
        return {"message": "Collections retrieved successfully.", "data": collections}
    except Exception as e:
        log_exception_with_request(e, retrieve_all_collections_for_agent, request)
        raise HTTPException(status_code=500, detail={
            "message": "Failed to retrieve collections.",
            "error": str(e)
        })

@router.get("/collections/files/{agent_id}/{collection_id}")
async def retrieve_all_files_for_collection(agent_id: str, collection_id: str, request: Request, user_id: str = None, limit: int = 20, skip: int = 0):
    """Return paginated list of files for a collection."""
    try:
        data = get_all_files_for_collection(agent_id, collection_id, user_id=user_id, limit=limit, skip=skip)
        return {"message": "Collection files retrieved successfully.", "data": data}
    except Exception as e:
        log_exception_with_request(e, retrieve_all_files_for_collection, request)
        raise HTTPException(status_code=500, detail={
            "message": "Failed to retrieve collection files.",
            "error": str(e)
        })
