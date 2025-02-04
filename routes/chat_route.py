from fastapi import APIRouter, HTTPException, Request, Body
from fastapi.responses import StreamingResponse
from llm.chat import chat
from errors.error_logger import log_exception_with_request
from typing import Optional

router = APIRouter()

@router.post("/agent/{session_id}")
async def chat_endpoint(
    session_id: str,
    agent_id: str,
    body: dict = Body(...),
    stream: Optional[bool] = False,
    use_rag: Optional[bool] = True,
    user_id: Optional[str] = None,
    request: Request = None
):
    try:
        message = body.get("message")
        if not message:
            raise ValueError("Message is required")

        if stream:
            return StreamingResponse(
                chat(
                    agent_id=agent_id,
                    session_id=session_id,
                    message=message,
                    stream=True,
                    use_rag=use_rag,
                    user_id=user_id
                ),
                media_type='text/event-stream'
            )
        else:
            response = chat(  # Removed await here
                agent_id=agent_id,
                session_id=session_id,
                message=message,
                stream=False,
                use_rag=use_rag,
                user_id=user_id
            )
            return {"response": response}

    except ValueError as e:
        code = 403 if "Not authorized" in str(e) else 400
        raise HTTPException(status_code=code, detail=str(e))
    except Exception as e:
        log_exception_with_request(e, chat_endpoint, request)
        raise HTTPException(status_code=500, detail="Internal Server Error")
