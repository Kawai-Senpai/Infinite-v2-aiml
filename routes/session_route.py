from fastapi import APIRouter, HTTPException, Request, Body
from llm.sessions import (
    create_session,
    delete_session,
    get_session_history,
    update_session_history,
    get_recent_history,
    get_all_sessions_for_user,
    get_agent_sessions_for_user,
    get_session,  # Add this import
)
from errors.error_logger import log_exception_with_request

router = APIRouter()

@router.post("/create")
async def create_session_endpoint(
    request: Request,
    agent_id: str,
    max_context_results: int = 1,
    user_id: str = None
):
    try:
        session_id = create_session(
            agent_id=agent_id,
            max_context_results=max_context_results,
            user_id=user_id
        )
        return {"session_id": session_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log_exception_with_request(e, create_session_endpoint, request)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.delete("/delete/{session_id}")
async def delete_session_endpoint(
    session_id: str,
    request: Request,
    user_id: str = None
):
    try:
        delete_session(session_id, user_id)
        return {"message": "Session deleted successfully"}
    except ValueError as e:
        code = 403 if "Not authorized" in str(e) else 404
        raise HTTPException(status_code=code, detail=str(e))
    except Exception as e:
        log_exception_with_request(e, delete_session_endpoint, request)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/history/{session_id}")
async def get_history_endpoint(
    session_id: str,
    request: Request,
    user_id: str = None,
    limit: int = 20,
    skip: int = 0
):
    try:
        history = get_session_history(session_id, user_id, limit=limit, skip=skip)
        return history
    except ValueError as e:
        code = 403 if "Not authorized" in str(e) else 404
        raise HTTPException(status_code=code, detail=str(e))
    except Exception as e:
        log_exception_with_request(e, get_history_endpoint, request)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.post("/history/update/{session_id}")
async def update_history_endpoint(
    session_id: str,
    request: Request,
    role: str,
    content: str,
    user_id: str = None
):
    try:
        update_session_history(session_id, role, content, user_id)
        return {"message": "History updated successfully"}
    except ValueError as e:
        code = 403 if "Not authorized" in str(e) else 404
        raise HTTPException(status_code=code, detail=str(e))
    except Exception as e:
        log_exception_with_request(e, update_history_endpoint, request)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/history/recent/{session_id}")
async def get_recent_history_endpoint(
    session_id: str,
    request: Request,
    max_history: int,
    user_id: str = None,
    limit: int = 20,
    skip: int = 0
):
    try:
        history = get_recent_history(
            session_id, 
            max_history, 
            user_id, 
            limit=limit, 
            skip=skip
        )
        return history
    except ValueError as e:
        code = 403 if "Not authorized" in str(e) else 404
        raise HTTPException(status_code=code, detail=str(e))
    except Exception as e:
        log_exception_with_request(e, get_recent_history_endpoint, request)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/get_all/{user_id}")
async def list_user_sessions(
    user_id: str,
    request: Request,
    limit: int = 20,
    skip: int = 0,
    sort_by: str = "created_at",
    sort_order: int = -1
):
    try:
        return get_all_sessions_for_user(
            user_id=user_id,
            limit=limit,
            skip=skip,
            sort_by=sort_by,
            sort_order=sort_order
        )
    except Exception as e:
        log_exception_with_request(e, list_user_sessions, request)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/get_by_agent/{agent_id}")
async def list_agent_sessions(
    agent_id: str,
    request: Request,
    user_id: str = None,
    limit: int = 20,
    skip: int = 0,
    sort_by: str = "created_at",
    sort_order: int = -1
):
    try:
        return get_agent_sessions_for_user(
            agent_id=agent_id,
            user_id=user_id,
            limit=limit,
            skip=skip,
            sort_by=sort_by,
            sort_order=sort_order
        )
    except ValueError as e:
        code = 403 if "Not authorized" in str(e) else 404
        raise HTTPException(status_code=code, detail=str(e))
    except Exception as e:
        log_exception_with_request(e, list_agent_sessions, request)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/get/{session_id}")
async def get_session_endpoint(
    session_id: str,
    request: Request,
    user_id: str = None,
    limit: int = 20,
    skip: int = 0
):
    try:
        session = get_session(
            session_id,
            user_id,
            limit=limit,
            skip=skip
        )
        return session
    except ValueError as e:
        code = 403 if "Not authorized" in str(e) else 404
        raise HTTPException(status_code=code, detail=str(e))
    except Exception as e:
        log_exception_with_request(e, get_session_endpoint, request)
        raise HTTPException(status_code=500, detail="Internal Server Error")
