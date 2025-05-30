from keys.keys import openai_api_key
from openai import OpenAI
from .prompts import make_query
from .schemas import CalculatorQuery
from utilities.save_json import extract_json_content
from ultraconfiguration import UltraConfig
import os

#! Initialize ---------------------------------------------------------------
config_path = os.path.join(os.path.dirname(__file__), "config.json")
config = UltraConfig(config_path)

client = OpenAI(api_key=openai_api_key)

def query_finder(message: str) -> dict:
    prompt = make_query(message)
    response = client.beta.chat.completions.parse(
        model=config.get("models.dicision"),
        messages=[{"role": "system", "content": prompt}],
        response_format=CalculatorQuery
    )
    content = response.choices[0].message.parsed
    if not content:
        return {
            "add": [],
            "sub": [],
            "mul": [],
            "div": []
        }
    return extract_json_content(content)

