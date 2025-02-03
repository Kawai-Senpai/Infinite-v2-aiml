from fastapi import FastAPI
from routes.agent_route import router as agent_router

app = FastAPI()

# Include the agent router at path "/agents"
app.include_router(agent_router, prefix="/agents", tags=["agents"])
