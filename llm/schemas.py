from pydantic import BaseModel, Field
from typing import List

#! Tool Analysis ---------------------------------------------------------------
class ToolAnalysisSchema(BaseModel):
    tools: List[str]

#! Memory ----------------------------------------------------------------------
class MemorySchema(BaseModel):
    to_remember: List[str]