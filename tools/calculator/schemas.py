from pydantic import BaseModel

#! Tool Analysis ---------------------------------------------------------------
class CalculatorQuery(BaseModel):
    add: list[float]
    sub: list[float]
    mul: list[float]
    div: list[float]