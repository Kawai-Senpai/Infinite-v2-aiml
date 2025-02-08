from fastapi import APIRouter, HTTPException, Request, Body
from llm.sessions import (
    create_session,
    delete_session,
    get_session_history,
    update_session_history,
    get_recent_history,
    get_all_sessions_for_user,
    get_agent_sessions_for_user,
    get_session,
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
        return {
            "message": "Chat session created successfully.",
            "session_id": session_id
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail={
            "message": "Failed to create session.",
            "error": str(e)
        })
    except Exception as e:
        log_exception_with_request(e, create_session_endpoint, request)
        raise HTTPException(status_code=500, detail={
            "message": "Internal Server Error while creating session.",
            "error": str(e)
        })

@router.delete("/delete/{session_id}")
async def delete_session_endpoint(
    session_id: str,
    request: Request,
    user_id: str = None
):
    try:
        delete_session(session_id, user_id)
        return {"message": "Chat session deleted successfully."}
    except ValueError as e:
        code = 403 if "Not authorized" in str(e) else 404
        raise HTTPException(status_code=code, detail={
            "message": "Failed to delete session.",
            "error": str(e)
        })
    except Exception as e:
        log_exception_with_request(e, delete_session_endpoint, request)
        raise HTTPException(status_code=500, detail={
            "message": "Internal Server Error while deleting session.",
            "error": str(e)
        })

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
        return {
            "message": "Session history retrieved successfully.",
            "data": history
        }
    except ValueError as e:
        code = 403 if "Not authorized" in str(e) else 404
        raise HTTPException(status_code=code, detail={
            "message": "Failed to retrieve session history.",
            "error": str(e)
        })
    except Exception as e:
        log_exception_with_request(e, get_history_endpoint, request)
        raise HTTPException(status_code=500, detail={
            "message": "Internal Server Error while retrieving history.",
            "error": str(e)
        })

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
        return {"message": "Session history updated successfully."}
    except ValueError as e:
        code = 403 if "Not authorized" in str(e) else 404
        raise HTTPException(status_code=code, detail={
            "message": "Failed to update session history.",
            "error": str(e)
        })
    except Exception as e:
        log_exception_with_request(e, update_history_endpoint, request)
        raise HTTPException(status_code=500, detail={
            "message": "Internal Server Error while updating session history.",
            "error": str(e)
        })

@router.get("/history/recent/{session_id}")
async def get_recent_history_endpoint(
    session_id: str,
    request: Request,
    user_id: str = None,
    limit: int = 20,
    skip: int = 0
):
    try:
        recent_history = get_recent_history(session_id, user_id, limit=limit, skip=skip)
        return {
            "message": "Recent session history retrieved successfully.",
            "data": recent_history
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail={
            "message": "Failed to retrieve recent history.",
            "error": str(e)
        })
    except Exception as e:
        log_exception_with_request(e, get_recent_history_endpoint, request)
        raise HTTPException(status_code=500, detail={
            "message": "Internal Server Error while retrieving recent history.",
            "error": str(e)
        })

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
        sessions = get_all_sessions_for_user(user_id, limit=limit, skip=skip, sort_by=sort_by, sort_order=sort_order)
        return {
            "message": "User sessions retrieved successfully.",
            "data": sessions
        }
    except Exception as e:
        log_exception_with_request(e, list_user_sessions, request)
        raise HTTPException(status_code=500, detail={
            "message": "Internal Server Error while retrieving user sessions.",
            "error": str(e)
        })

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
        sessions = get_agent_sessions_for_user(agent_id, user_id=user_id, limit=limit, skip=skip, sort_by=sort_by, sort_order=sort_order)
        return {
            "message": "Agent sessions retrieved successfully.",
            "data": sessions
        }
    except ValueError as e:
        raise HTTPException(status_code=403, detail={
            "message": "Not authorized to view sessions for this agent.",
            "error": str(e)
        })
    except Exception as e:
        log_exception_with_request(e, list_agent_sessions, request)
        raise HTTPException(status_code=500, detail={
            "message": "Internal Server Error while retrieving agent sessions.",
            "error": str(e)
        })

@router.get("/get/{session_id}")
async def get_session_endpoint(
    session_id: str,
    request: Request,
    user_id: str = None,
    limit: int = 20,
    skip: int = 0
):
    try:
        session = get_session(session_id, user_id, limit=limit, skip=skip)
        return {
            "message": "Session details retrieved successfully.",
            "data": session
        }
    except ValueError as e:
        raise HTTPException(status_code=403, detail={
            "message": "Failed to retrieve session details.",
            "error": str(e)
        })
    except Exception as e:
        log_exception_with_request(e, get_session_endpoint, request)
        raise HTTPException(status_code=500, detail={
            "message": "Internal Server Error while retrieving session details.",
            "error": str(e)
        })
