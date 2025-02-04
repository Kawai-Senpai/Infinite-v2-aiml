from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from llm.chat import chat
from errors.error_logger import log_exception_with_request
from typing import Optional

router = APIRouter()

@router.post("/chat/{session_id}")
async def chat_endpoint(
    session_id: str,
    message: str,
    agent_id: str,
    stream: Optional[bool] = False,
    use_rag: Optional[bool] = True,
    user_id: Optional[str] = None,
    request: Request = None
):
    try:
        if stream:
            # Return streaming response
            return StreamingResponse(
                chat(
                    agent_id=agent_id,
                    session_id=session_id,
                    message=message,
                    stream=True,
                    use_rag=use_rag,
                    user_id=user_id  # Add user_id here
                ),
                media_type='text/event-stream'
            )
        else:
            # Return normal response
            response = chat(
                agent_id=agent_id,
                session_id=session_id,
                message=message,
                stream=False,
                use_rag=use_rag,
                user_id=user_id  # Add user_id here
            )
            return {"response": response}

    except ValueError as e:
        code = 403 if "Not authorized" in str(e) else 400  # Add 403 for authorization errors
        raise HTTPException(status_code=code, detail=str(e))
    except Exception as e:
        log_exception_with_request(e, chat_endpoint, request)
        raise HTTPException(status_code=500, detail="Internal Server Error")
