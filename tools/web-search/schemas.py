from pydantic import BaseModel

#! Tool Analysis ---------------------------------------------------------------
class ToolQuery(BaseModel):
    query: list[str]