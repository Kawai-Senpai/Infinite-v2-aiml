from fastapi import APIRouter, HTTPException, Request, Body
from fastapi.responses import StreamingResponse
from llm.chat import chat, team_chat, team_chat_managed, team_chat_flow
from errors.error_logger import log_exception_with_request
from typing import Optional
from bson import ObjectId
from database.mongo import client as mongo_client

router = APIRouter()

@router.post("/agent/{session_id}")
async def chat_endpoint(
    session_id: str,
    agent_id: str,
    body: dict = Body(...),
    stream: Optional[bool] = False,
    use_rag: Optional[bool] = True,
    include_rich_response: Optional[bool] = True,
    user_id: Optional[str] = None,
    request: Request = None
):
    try:
        db = mongo_client.ai
        session_doc = db.sessions.find_one({"_id": ObjectId(session_id)})
        if not session_doc:
            raise HTTPException(status_code=404, detail="Session not found")
        if session_doc.get("session_type") == "team":
            raise HTTPException(
                status_code=400,
                detail="Cannot use /agent endpoint for team sessions"
            )

        message = body.get("message")
        # New check for empty or whitespace-only message
        if not message or not message.strip():
            raise ValueError("Message is required and cannot be empty")
        
        if stream:
            return StreamingResponse(
                chat(
                    agent_id=agent_id,
                    session_id=session_id,
                    message=message,
                    stream=True,
                    use_rag=use_rag,
                    user_id=user_id,
                    include_rich_response=include_rich_response
                ),
                media_type='text/event-stream'
            )
        else:
            response = chat(
                agent_id=agent_id,
                session_id=session_id,
                message=message,
                stream=False,
                use_rag=use_rag,
                user_id=user_id,
                include_rich_response=include_rich_response
            )
            return {
                "message": "Chat completed successfully.",
                "response": response
            }
    except ValueError as e:
        code = 403 if "Not authorized" in str(e) else 400
        raise HTTPException(status_code=code, detail={
            "message": "Chat request failed.",
            "error": str(e)
        })
    except Exception as e:
        log_exception_with_request(e, chat_endpoint, request)
        raise HTTPException(status_code=500, detail={
            "message": "Internal Server Error during chat.",
            "error": str(e)
        })

@router.post("/team/{session_id}")
async def team_chat_endpoint(
    session_id: str,
    body: dict = Body(...),  # Change to accept dict instead of individual parameters
    stream: bool = False,
    use_rag: bool = True,
    include_rich_response: bool = True,
    user_id: Optional[str] = None,
    request: Request = None
):
    try:
        db = mongo_client.ai
        session_doc = db.sessions.find_one({"_id": ObjectId(session_id)})
        if not session_doc:
            raise HTTPException(status_code=404, detail="Session not found")

        session_type = session_doc.get("session_type")
        if not session_type or not session_type.startswith("team"):
            raise HTTPException(status_code=400, detail="Not a team session")

        message = body.get("message", "")
        if not message or not message.strip():
            raise ValueError("Message is required and cannot be empty")

        if session_type == "team":
            chat_func = team_chat
        elif session_type == "team-managed":
            chat_func = team_chat_managed
        elif session_type == "team-flow":
            chat_func = team_chat_flow
        else:
            raise HTTPException(status_code=400, detail="Unknown team session type")

        if stream:
            return StreamingResponse(
                chat_func(
                    session_id=session_id,
                    message=message,
                    stream=True,
                    use_rag=use_rag,
                    user_id=user_id,
                    include_rich_response=include_rich_response
                ),
                media_type='text/event-stream'
            )
        else:
            response = chat_func(
                session_id=session_id,
                message=message,
                stream=False,
                use_rag=use_rag,
                user_id=user_id,
                include_rich_response=include_rich_response
            )
            # Ensure we return a valid JSON response
            return {"status": "success", "data": response}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log_exception_with_request(e, request)
        raise HTTPException(status_code=500, detail=str(e))
