from keys.keys import openai_api_key, environment
import json
from openai import OpenAI
from llm.prompts import make_tool_analysis_prompt, make_memory_analysis_prompt
from ultraconfiguration import UltraConfig
from ultraprint.logging import logger
from llm.schemas import ToolAnalysisSchema, MemorySchema
from utilities.save_json import extract_json_content

#! Initialize ---------------------------------------------------------------
config = UltraConfig('config.json')
log = logger('decision_log', 
            filename='debug/decision.log', 
            include_extra_info=config.get("logging.include_extra_info", False), 
            write_to_file=config.get("logging.write_to_file", False), 
            log_level=config.get("logging.development_level", "DEBUG") if environment == 'development' else config.get("logging.production_level", "INFO"))

client = OpenAI(api_key=openai_api_key)

def analyze_tool_need(message: str, available_tools: list) -> dict:
    """Analyze if a tool is needed for the message"""
    prompt = make_tool_analysis_prompt(message, available_tools)
    response = client.beta.chat.completions.parse(
        model=config.get("models.dicision"),
        messages=[{"role": "system", "content": prompt}],
        response_format=ToolAnalysisSchema
    )
    content = response.choices[0].message.parsed
    if not content:
        return {"tools": []}
    return extract_json_content(content)

def analyze_for_memory(message: str) -> dict:
    """Analyze if the message contains important information to remember"""
    prompt = make_memory_analysis_prompt(message)
    response = client.beta.chat.completions.parse(
        model=config.get("models.dicision"),
        messages=[{"role": "system", "content": prompt}],
        response_format=MemorySchema
    )
    content = response.choices[0].message.parsed
    if not content:
        return {"to_remember": []}
    return extract_json_content(content)

