from fastapi import APIRouter, HTTPException, Request, Body, Query
from typing import Optional
from llm.sessions import (
    create_session,
    delete_session,
    get_session_history,
    update_session_history,
    get_recent_history,
    get_all_sessions_for_user,
    get_agent_sessions_for_user,
    get_session,
    create_team_session,
    get_team_session_history,
    update_team_session_history,
    get_team_sessions_for_user,
    get_standalone_sessions_for_user,
    update_session_name
)
from errors.error_logger import log_exception_with_request

router = APIRouter()

@router.post("/create")
async def create_session_endpoint(
    request: Request,
    agent_id: str,
    max_context_results: int = 1,
    name: str = None,          # new optional parameter
    user_id: str = None
):
    try:
        session_id = create_session(
            agent_id=agent_id,
            max_context_results=max_context_results,
            user_id=user_id,
            name=name           # pass optional name
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

@router.post("/team/create")
async def create_team_session_endpoint(
    request: Request,
    agent_ids: list = Body(...),
    max_context_results: int = 1,
    name: str = None,              # Changed from Body(None) to parameter
    user_id: str = None,
    session_type: str = "team"
):
    try:
        session_id = create_team_session(
            agent_ids=agent_ids,
            max_context_results=max_context_results,
            user_id=user_id,
            session_type=session_type,
            name=name                # Pass name as parameter
        )
        return {
            "message": "Team session created successfully.",
            "session_id": session_id
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail={
            "message": "Failed to create team session.",
            "error": str(e)
        })
    except Exception as e:
        log_exception_with_request(e, create_team_session_endpoint, request)
        raise HTTPException(status_code=500, detail={
            "message": "Internal Server Error while creating team session.",
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

@router.get("/team/history/{session_id}")
async def get_team_session_history_endpoint(
    session_id: str,
    request: Request,
    user_id: str = None,
    limit: int = 20,
    skip: int = 0
):
    try:
        history = get_team_session_history(session_id, user_id, limit, skip)
        return {
            "message": "Team session history retrieved successfully.",
            "data": history
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail={
            "message": "Failed to retrieve team session history.",
            "error": str(e)
        })
    except Exception as e:
        log_exception_with_request(e, get_team_session_history_endpoint, request)
        raise HTTPException(status_code=500, detail={
            "message": "Internal Server Error while retrieving team session history.",
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
        update_session_history(session_id, role, content, user_id=user_id)  # Fixed call: pass user_id as keyword argument
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

@router.post("/team/history/update/{session_id}")
async def update_team_session_history_endpoint(
    session_id: str,
    request: Request,
    agent_id: str = Body(None),
    role: str = Body(...),
    content: str = Body(...),
    user_id: str = None,
    summary: bool = False
):
    try:
        update_team_session_history(session_id, agent_id, role, content, user_id=user_id, summary=summary)
        return {"message": "Team session history updated successfully."}
    except ValueError as e:
        raise HTTPException(status_code=403, detail={
            "message": "Failed to update team session history.",
            "error": str(e)
        })
    except Exception as e:
        log_exception_with_request(e, update_team_session_history_endpoint, request)
        raise HTTPException(status_code=500, detail={
            "message": "Internal Server Error while updating team session history.",
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

@router.get("/get_all_team/{user_id}")
async def list_user_team_sessions(
    user_id: str,
    request: Request,
    limit: int = 20,
    skip: int = 0,
    sort_by: str = "created_at",
    sort_order: int = -1
):
    try:
        sessions = get_team_sessions_for_user(
            user_id, limit=limit, skip=skip, sort_by=sort_by, sort_order=sort_order
        )
        return {
            "message": "Team sessions retrieved successfully.",
            "data": sessions
        }
    except Exception as e:
        log_exception_with_request(e, list_user_team_sessions, request)
        raise HTTPException(status_code=500, detail={
            "message": "Internal Server Error while retrieving team sessions.",
            "error": str(e)
        })

@router.get("/get_all_standalone/{user_id}")
async def list_user_standalone_sessions(
    user_id: str,
    request: Request,
    limit: int = 20,
    skip: int = 0,
    sort_by: str = "created_at",
    sort_order: int = -1
):
    try:
        sessions = get_standalone_sessions_for_user(
            user_id, limit=limit, skip=skip, sort_by=sort_by, sort_order=sort_order
        )
        return {
            "message": "Standalone sessions retrieved successfully.",
            "data": sessions
        }
    except Exception as e:
        log_exception_with_request(e, list_user_standalone_sessions, request)
        raise HTTPException(status_code=500, detail={
            "message": "Internal Server Error while retrieving standalone sessions.",
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

@router.put("/rename/{session_id}")
async def rename_session_endpoint(
    session_id: str,
    request: Request,  # Add request parameter
    name: str,
    user_id: str = None
):
    try:
        update_session_name(session_id, name, user_id)
        return {"message": "Session renamed successfully."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"message": "Failed to rename session.", "error": str(e)})
    except Exception as e:
        log_exception_with_request(e, rename_session_endpoint, request)  # Add logging
        raise HTTPException(status_code=500, detail={"message": "Internal Server Error.", "error": str(e)})

@router.get("/get/{session_id}")
async def get_session_details(
    session_id: str,
    limit: int = Query(20, ge=1),
    skip: int = Query(0, ge=0),
    user_id: Optional[str] = None,
    request: Request = None  # Add request parameter
):
    try:
        session_data = get_session(session_id, user_id=user_id, limit=limit, skip=skip)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        return session_data
    except HTTPException:
        raise
    except Exception as e:
        log_exception_with_request(e, get_session_details, request)  # Add logging
        raise HTTPException(status_code=500, detail=str(e))
