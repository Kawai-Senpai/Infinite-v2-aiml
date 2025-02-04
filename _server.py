from fastapi import FastAPI
from datetime import datetime, timezone
from routes.agent_route import router as agent_router
from routes.session_route import router as session_router
from routes.chat_route import router as chat_router
from errors.error_logger import log_exception_with_request
from database.mongo import pingtest as mongo_pingtest
from database.chroma import pingtest as chroma_pingtest 
from fastapi import Request
import uvicorn

app = FastAPI()

app.include_router(agent_router, prefix="/agents", tags=["agents"])
app.include_router(session_router, prefix="/sessions", tags=["sessions"])
app.include_router(chat_router, prefix="/chat", tags=["chat"])

# New async status route
@app.get("/status")
@app.get("/")
async def status(request: Request):
    try:
        mongo_status = "up" if mongo_pingtest() else "down"
        chroma_status = "up" if chroma_pingtest() else "down"
        return {
            "server": "AIML",
            "time": datetime.now(timezone.utc).isoformat() + "Z",  # current UTC time
            "mongodb": mongo_status,
            "chromadb": chroma_status
        }
    except Exception as e:
        log_exception_with_request(e, status, request)
        return {
            "server": "AIML",
            "time": datetime.now(timezone.utc).isoformat() + "Z",  # current UTC time
            "mongodb": "down",
            "chromadb": "down"
        }

if __name__ == "__main__":
    uvicorn.run("_server:app", host="localhost", port=8000, reload=True)