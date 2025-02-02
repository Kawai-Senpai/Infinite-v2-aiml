from keys.keys import openai_api_key
import json
from openai import OpenAI
from llm.prompts import make_tool_analysis_prompt, make_memory_analysis_prompt

client = OpenAI(api_key=openai_api_key)

def analyze_tool_need(message: str, available_tools: list) -> dict:
    """Analyze if a tool is needed for the message"""
    prompt = make_tool_analysis_prompt(message, available_tools)
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return json.loads(response.choices[0].message.content)

def analyze_for_memory(message: str) -> dict:
    """Analyze if the message contains important information to remember"""
    prompt = make_memory_analysis_prompt(message)
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt.format(message=message)}],
        temperature=0
    )
    return json.loads(response.choices[0].message.content)

