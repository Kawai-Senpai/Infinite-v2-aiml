from pydantic import BaseModel, Field
from typing import List

#! Tool Analysis ---------------------------------------------------------------
class ToolAnalysisSchema(BaseModel):
    """
    Schema for analyzing tool needs.

    Attributes:
        tools (List[str]): A list of tool names required for a message.
    """
    tools: List[str]

#! Memory ----------------------------------------------------------------------
class MemorySchema(BaseModel):
    """
    Schema for memory analysis.

    Attributes:
        to_remember (List[str]): A list of important information to remember.
    """
    to_remember: List[str]

#! Summary Schema --------------------------------------------------------------
class SummarySchema(BaseModel):
    """
    Schema for summarizing chat history.

    Attributes:
        summary (str): A summary of the chat history.
    """
    summary: str

#! Team Chat Schema ------------------------------------------------------------
#? Managed Agents --------------------------------------------------------------
class ManagedAgentSchema(BaseModel):
    """
    Schema for managed agent order.

    Attributes:
        agent_order (List[str]): A list of agent IDs in the order they should respond.
    """
    agent_order: List[str]

#? Flow Agents ---------------------------------------------------------------
class FlowAgentSchema(BaseModel):
    """
    Schema for flow agent decision.

    Attributes:
        next_agent (str): The ID of the next agent to respond.
    """
    next_agent: str