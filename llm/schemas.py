from pydantic import BaseModel, Field
from typing import List

#! Tool Analysis ---------------------------------------------------------------
class Tool(BaseModel):
    name: str
    query: str

class ToolAnalysisSchema(BaseModel):
    tools: List[Tool]

#! Memory ----------------------------------------------------------------------
class MemorySchema(BaseModel):
    to_remember: List[str]