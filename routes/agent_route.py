from fastapi import APIRouter, HTTPException, Request
from typing import Optional
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

@router.post("/create")
def create_agent_endpoint(
    request: Request,
    name: str,
    role: str = "",
    capabilities: list = [],
    rules: list = [],
    model_provider: str = "openai",
    model: str = "gpt-4o",
    max_history: int = 20,
    tools: list = [],
    num_collections: int = 1,
    max_memory_size: int = 1,
    user_id: Optional[str] = None,
    agent_type: str = "private"
):
    try:
        agent_id = create_agent(
            name=name,
            role=role,
            capabilities=capabilities,
            rules=rules,
            model_provider=model_provider,
            model=model,
            max_history=max_history,
            tools=tools,
            num_collections=num_collections,
            max_memory_size=max_memory_size,
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
def delete_agent_endpoint(agent_id: str, request: Request):
    try:
        delete_agent(agent_id)
        return {"message": f"Agent {agent_id} deleted successfully."}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log_exception_with_request(e, delete_agent_endpoint, request)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/get_public")
def list_public_agents(request: Request):
    try:
        return get_all_public_agents()
    except Exception as e:
        log_exception_with_request(e, list_public_agents, request)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/get_approved")
def list_approved_agents(request: Request):
    try:
        return get_all_approved_agents()
    except Exception as e:
        log_exception_with_request(e, list_approved_agents, request)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/get_system")
def list_system_agents(request: Request):
    try:
        return get_all_system_agents()
    except Exception as e:
        log_exception_with_request(e, list_system_agents, request)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/get_user/{user_id}")
def list_user_agents(user_id: str, request: Request):
    try:
        return get_all_agents_for_user(user_id)
    except Exception as e:
        log_exception_with_request(e, list_user_agents, request)
        raise HTTPException(status_code=500, detail="Internal Server Error")
