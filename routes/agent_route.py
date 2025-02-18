from fastapi import APIRouter, HTTPException, Request, Body, Query  # ensure Query is imported
from llm.agents import (
    create_agent,
    delete_agent,
    update_agent,  # Add this import
    get_all_public_agents,
    get_all_approved_agents,
    get_all_system_agents,
    get_all_agents_for_user,
    get_agent,
    get_available_tools,
    get_all_nonprivate_agents_for_user,
    search_agents  # add import for search
)
from errors.error_logger import log_exception_with_request

router = APIRouter()

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
            max_memory_size=body.get("max_memory_size", 5),
            user_id=user_id,
            agent_type=agent_type
        )
        return {
            "message": "Agent created successfully.",
            "agent_id": str(agent_id)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail={
            "message": "Failed to create agent.",
            "error": str(e)
        })
    except Exception as e:
        log_exception_with_request(e, create_agent_endpoint, request)
        raise HTTPException(status_code=500, detail={
            "message": "Internal Server Error while creating agent.",
            "error": str(e)
        })

@router.delete("/delete/{agent_id}")
async def delete_agent_endpoint(agent_id: str, user_id: str = None, request: Request = None):
    try:
        delete_agent(agent_id, user_id)
        return {"message": f"Agent '{agent_id}' deleted successfully."}
    except ValueError as e:
        code = 403 if "Not authorized" in str(e) else 404
        raise HTTPException(status_code=code, detail={
            "message": "Failed to delete agent.",
            "error": str(e)
        })
    except Exception as e:
        log_exception_with_request(e, delete_agent_endpoint, request)
        raise HTTPException(status_code=500, detail={
            "message": "Internal Server Error while deleting agent.",
            "error": str(e)
        })

@router.put("/update/{agent_id}")
async def update_agent_endpoint(
    agent_id: str,
    user_id: str = None,
    request: Request = None,
    body: dict = Body(...)
):
    try:
        success = update_agent(
            agent_id=agent_id,
            user_id=user_id,
            **body
        )
        return {
            "message": "Agent updated successfully.",
            "success": success
        }
    except ValueError as e:
        code = 403 if "Not authorized" in str(e) else 404
        raise HTTPException(status_code=code, detail={
            "message": "Failed to update agent.",
            "error": str(e)
        })
    except Exception as e:
        log_exception_with_request(e, update_agent_endpoint, request)
        raise HTTPException(status_code=500, detail={
            "message": "Internal Server Error while updating agent.",
            "error": str(e)
        })

@router.get("/get_public")
async def list_public_agents(
    request: Request, 
    limit: int = 20, 
    skip: int = 0, 
    sort_by: str = "created_at",
    sort_order: int = -1
):
    try:
        agents = get_all_public_agents(limit=limit, skip=skip, sort_by=sort_by, sort_order=sort_order)
        return {
            "message": "Public agents retrieved successfully.",
            "data": agents
        }
    except Exception as e:
        log_exception_with_request(e, list_public_agents, request)
        raise HTTPException(status_code=500, detail={
            "message": "Internal Server Error while retrieving public agents.",
            "error": str(e)
        })

@router.get("/get_approved")
async def list_approved_agents(
    request: Request, 
    limit: int = 20, 
    skip: int = 0, 
    sort_by: str = "created_at",
    sort_order: int = -1
):
    try:
        agents = get_all_approved_agents(limit=limit, skip=skip, sort_by=sort_by, sort_order=sort_order)
        return {
            "message": "Approved agents retrieved successfully.",
            "data": agents
        }
    except Exception as e:
        log_exception_with_request(e, list_approved_agents, request)
        raise HTTPException(status_code=500, detail={
            "message": "Internal Server Error while retrieving approved agents.",
            "error": str(e)
        })

@router.get("/get_system")
async def list_system_agents(
    request: Request, 
    limit: int = 20, 
    skip: int = 0, 
    sort_by: str = "created_at",
    sort_order: int = -1
):
    try:
        agents = get_all_system_agents(limit=limit, skip=skip, sort_by=sort_by, sort_order=sort_order)
        return {
            "message": "System agents retrieved successfully.",
            "data": agents
        }
    except Exception as e:
        log_exception_with_request(e, list_system_agents, request)
        raise HTTPException(status_code=500, detail={
            "message": "Internal Server Error while retrieving system agents.",
            "error": str(e)
        })

@router.get("/get_user/{user_id}")
async def list_user_agents(
    user_id: str, 
    request: Request, 
    limit: int = 20, 
    skip: int = 0, 
    sort_by: str = "created_at",
    sort_order: int = -1
):
    try:
        agents = get_all_agents_for_user(user_id, limit=limit, skip=skip, sort_by=sort_by, sort_order=sort_order)
        return {
            "message": "User agents retrieved successfully.",
            "data": agents
        }
    except Exception as e:
        log_exception_with_request(e, list_user_agents, request)
        raise HTTPException(status_code=500, detail={
            "message": "Internal Server Error while retrieving user agents.",
            "error": str(e)
        })

@router.get("/get_user_nonprivate/{user_id}")
async def list_user_nonprivate_agents(
    user_id: str, 
    request: Request, 
    limit: int = 20, 
    skip: int = 0, 
    sort_by: str = "created_at",
    sort_order: int = -1
):
    try:
        agents = get_all_nonprivate_agents_for_user(user_id, limit=limit, skip=skip, sort_by=sort_by, sort_order=sort_order)
        return {
            "message": "User non-private agents retrieved successfully.",
            "data": agents
        }
    except Exception as e:
        log_exception_with_request(e, list_user_nonprivate_agents, request)
        raise HTTPException(status_code=500, detail={
            "message": "Internal Server Error while retrieving user non-private agents.",
            "error": str(e)
        })

@router.get("/get/{agent_id}")
async def get_agent_details(agent_id: str, user_id: str = None, request: Request = None):
    try:
        agent = get_agent(agent_id, user_id)
        return {
            "message": "Agent details retrieved successfully.",
            "data": agent
        }
    except ValueError as e:
        code = 403 if "Not authorized" in str(e) else 404
        raise HTTPException(status_code=code, detail={
            "message": "Failed to retrieve agent details.",
            "error": str(e)
        })
    except Exception as e:
        log_exception_with_request(e, get_agent_details, request)
        raise HTTPException(status_code=500, detail={
            "message": "Internal Server Error while retrieving agent details.",
            "error": str(e)
        })

@router.get("/tools")
async def list_available_tools(request: Request):
    try:
        tools = get_available_tools()
        return {
            "message": "Available tools retrieved successfully.",
            "data": tools
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail={
            "message": "Failed to retrieve available tools.",
            "error": str(e)
        })
    except Exception as e:
        log_exception_with_request(e, list_available_tools, request)
        raise HTTPException(status_code=500, detail={
            "message": "Internal Server Error while retrieving available tools.",
            "error": str(e)
        })

@router.get("/search")
async def search_agent(
    request: Request,
    query: str = Query(..., description="Search term for agent names, capabilities or rules"),
    limit: int = 20,
    skip: int = 0
):
    try:
        agents = search_agents(query, limit, skip)
        return {
            "message": "Agents retrieved successfully.",
            "data": agents
        }
    except Exception as e:
        log_exception_with_request(e, search_agent, request)
        raise HTTPException(status_code=500, detail={
            "message": "Internal Server Error while searching agents.",
            "error": str(e)
        })
