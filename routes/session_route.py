from fastapi import APIRouter, HTTPException, Request
from llm.sessions import (
    create_session,
    delete_session,
    get_session_history,
    update_session_history,
    get_recent_history,
    get_all_sessions_for_user,
    get_agent_sessions_for_user
)
from errors.error_logger import log_exception_with_request

router = APIRouter()

@router.get("/get/{user_id}")
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
