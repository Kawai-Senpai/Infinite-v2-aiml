from ultraconfiguration import UltraConfig
import os
from .decision import query_finder

#! Initialize ---------------------------------------------------------------
config_path = os.path.join(os.path.dirname(__file__), "config.json")
config = UltraConfig(config_path)

#* Web search ---------------------------------------------------------------
def calculate(message: str) -> dict:
    """Perform web search using DuckDuckGo"""
    try:
        querys = query_finder(message)
        addition = querys.get("add", [])
        subtract = querys.get("sub", [])
        multiply = querys.get("mul", [])
        divide = querys.get("div", [])

        formatted_results = []
        structured_data = []
        if addition:
            add = 0
            for a in addition:
                add += a
            formatted_results.append(f"Addition of {addition} = {add}")
            structured_data.append({
                "operation": "add",
                "operands": addition,
                "result": add
            })
        if subtract:
            sub = subtract[0]
            for s in subtract[1:]:
                sub -= s
            formatted_results.append(f"Subtraction of {subtract} = {sub}")
            structured_data.append({
                "operation": "subtract",
                "operands": subtract,
                "result": sub
            })
        if multiply:
            mul = 1
            for m in multiply:
                mul *= m
            formatted_results.append(f"Multiplication of {multiply} = {mul}")
            structured_data.append({
                "operation": "multiply",
                "operands": multiply,
                "result": mul
            })
        if divide:
            div = divide[0]
            for d in divide[1:]:
                if d == 0:
                    div = "Infinity"
                    break
                div /= d
            formatted_results.append(f"Division of {divide} = {div}")
            structured_data.append({
                "operation": "divide",
                "operands": divide,
                "result": div
            })

        text_output = "\n".join(formatted_results) if formatted_results else ""
        return {
            "text": text_output,
            "data": structured_data
        }
    except Exception as e:
        return {
            "text": "",
            "data": []
        }