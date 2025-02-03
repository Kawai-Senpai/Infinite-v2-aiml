from fastapi import APIRouter, HTTPException, Request, Body
from llm.agents import (
    create_agent,
    delete_agent,
    get_all_public_agents,
    get_all_approved_agents,
    get_all_system_agents,
    get_all_agents_for_user
)
from errors.error_logger import log_exception_with_request

router = APIRouter()

# Removed CreateAgentBody model

@router.post("/create")
async def create_agent_endpoint(
    request: Request,
    user_id: str,       
    agent_type: str,   
    name: str,       
    body: dict = Body(...)  # the rest from the body as a plain dict
):
    try:
        agent_id = create_agent(
            name=name,
            role=body.get("role", ""),
            capabilities=body.get("capabilities", []),
            rules=body.get("rules", []),
            model_provider=body.get("model_provider", "openai"),
            model=body.get("model", "gpt-4o"),
            max_history=body.get("max_history", 20),
            tools=body.get("tools", []),
            num_collections=body.get("num_collections", 1),
            max_memory_size=body.get("max_memory_size", 1),
            user_id=user_id,
            agent_type=agent_type
        )
        return {"agent_id": str(agent_id)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log_exception_with_request(e, create_agent_endpoint, request)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.delete("/delete/{agent_id}")
async def delete_agent_endpoint(agent_id: str, request: Request):
    try:
        delete_agent(agent_id)
        return {"message": f"Agent {agent_id} deleted successfully."}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log_exception_with_request(e, delete_agent_endpoint, request)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/get_public")
async def list_public_agents(request: Request):
    try:
        return get_all_public_agents()
    except Exception as e:
        log_exception_with_request(e, list_public_agents, request)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/get_approved")
async def list_approved_agents(request: Request):
    try:
        return get_all_approved_agents()
    except Exception as e:
        log_exception_with_request(e, list_approved_agents, request)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/get_system")
async def list_system_agents(request: Request):
    try:
        return get_all_system_agents()
    except Exception as e:
        log_exception_with_request(e, list_system_agents, request)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/get_user/{user_id}")
async def list_user_agents(user_id: str, request: Request):
    try:
        return get_all_agents_for_user(user_id)
    except Exception as e:
        log_exception_with_request(e, list_user_agents, request)
        raise HTTPException(status_code=500, detail="Internal Server Error")
