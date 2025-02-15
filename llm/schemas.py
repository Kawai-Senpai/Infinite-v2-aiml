from pydantic import BaseModel, Field
from typing import List

#! Tool Analysis ---------------------------------------------------------------
class ToolAnalysisSchema(BaseModel):
    tools: List[str]

#! Memory ----------------------------------------------------------------------
class MemorySchema(BaseModel):
    to_remember: List[str]

#! Summary Schema --------------------------------------------------------------
class SummarySchema(BaseModel):
    summary: str

#! Team Chat Schema ------------------------------------------------------------
#? Managed Agents --------------------------------------------------------------
class ManagedAgentSchema(BaseModel):
    agent_order: List[str]

#? Flow Agents ---------------------------------------------------------------
class FlowAgentSchema(BaseModel):
    next_agent: str