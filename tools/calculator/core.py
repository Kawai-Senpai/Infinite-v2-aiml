from ultraconfiguration import UltraConfig
import os
from .decision import query_finder

#! Initialize ---------------------------------------------------------------
config_path = os.path.join(os.path.dirname(__file__), "config.json")
config = UltraConfig(config_path)

#* Web search ---------------------------------------------------------------
def calculate(message: str) -> str:
    """Perform web search using DuckDuckGo"""
    try:
        querys = query_finder(message)
        addition = querys.get("add", [])
        subtract = querys.get("sub", [])
        multiply = querys.get("mul", [])
        divide = querys.get("div", [])

        formatted_results = []
        if addition:
            add = 0
            for a in addition:
                add += a
            formatted_results.append(f"Addition of {addition} = {add}")
        if subtract:
            sub = subtract[0]
            for s in subtract[1:]:
                sub -= s
            formatted_results.append(f"Subtraction of {subtract} = {sub}")
        if multiply:
            mul = 1
            for m in multiply:
                mul *= m
            formatted_results.append(f"Multiplication of {multiply} = {mul}")
        if divide:
            div = divide[0]
            for d in divide[1:]:
                if d == 0:
                    div = "Infinity"
                    break
                div /= d
            formatted_results.append(f"Division of {divide} = {div}")

        return "\n".join(formatted_results) if formatted_results else ""
    except Exception as e:
        return ""