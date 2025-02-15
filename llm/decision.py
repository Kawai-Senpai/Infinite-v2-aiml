from keys.keys import openai_api_key, environment
import json
from openai import OpenAI
from llm.prompts import make_tool_analysis_prompt, make_memory_analysis_prompt, make_summary_prompt, make_agent_decider_prompt_managed, make_agent_decider_prompt_flow
from ultraconfiguration import UltraConfig
from ultraprint.logging import logger
from llm.schemas import ToolAnalysisSchema, MemorySchema, SummarySchema, ManagedAgentSchema, FlowAgentSchema
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
    log.debug("Tool analysis response: %s", content)
    if not content:
        return {"tools": []}
    return extract_json_content(content)

def analyze_for_memory(message: str) -> dict:
    """Analyze if the message contains important information to remember"""
    try:
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
    except Exception as e:
        log.error("Error analyzing for memory: %s", e)
        return {"to_remember": []}

def summarize_chat_history(chat_history: list, num_messages = None) -> dict:
    """
    Summarize the latest chat history messages.
    chat_history: list of dicts with keys 'role' and 'content'
    num_messages: number of latest messages to consider for summary

    Returns a dict like { "summary": "..." }
    """
    # Select the latest messages
    if not num_messages:
        recent_messages = chat_history
    else:
        recent_messages = chat_history[-num_messages:]

    if not recent_messages:
        return {"summary": ""}

    processed_messages = []
    for msg in recent_messages:
        if msg.get("type") == "summary":
            processed_messages.append("Summary: " + msg['content'])
        elif msg.get("agent_name"):
            processed_messages.append(f"{msg['agent_name']}: {msg['content']}")
        else:
            processed_messages.append(f"{msg['role']}: {msg['content']}")
    conversation_text = "\n".join(processed_messages)

    prompt = make_summary_prompt(conversation_text)
    
    response = client.beta.chat.completions.parse(
        model=config.get("models.dicision"),
        messages=[{"role": "system", "content": prompt}],
        response_format=SummarySchema
    )
    content = response.choices[0].message.parsed
    if not content:
        return {"summary": ""}
    return extract_json_content(content)

#! Team Chat ---------------------------------------------------------------
def team_managed_decision(message, chat_history, num_messages=None, all_agents=None):

    if all_agents is None:
        return {"agent_order": []}
    
    # Select the latest messages
    if not num_messages:
        recent_messages = chat_history
    else:
        recent_messages = chat_history[-num_messages:]

    processed_messages = []
    for msg in recent_messages:
        if msg.get("type") == "summary":
            processed_messages.append("Summary: " + msg['content'])
        elif msg.get("agent_name"):
            processed_messages.append(f"{msg['agent_name']}: {msg['content']}")
        else:
            processed_messages.append(f"{msg['role']}: {msg['content']}")
    conversation_text = "\n".join(processed_messages)

    prompt = make_agent_decider_prompt_managed(message, all_agents=all_agents)

    response = client.beta.chat.completions.parse(
        model=config.get("models.dicision"),
        messages=[{"role": "system", "content": prompt}],
        response_format=ManagedAgentSchema
    )
    content = response.choices[0].message.parsed
    if not content:
        return {"agent_order": []}
    return extract_json_content(content)

def team_flow_decision(chat_history, num_messages=None, all_agents=None):
    """Decide next agent in flow based on conversation history."""
    if all_agents is None:
        return {"next_agent": ""}
    
    # Select the latest messages
    if not num_messages:
        recent_messages = chat_history
    else:
        recent_messages = chat_history[-num_messages:]

    processed_messages = []
    for msg in recent_messages:
        if msg.get("type") == "summary":
            processed_messages.append("Summary: " + msg['content'])
        elif msg.get("agent_name"):
            processed_messages.append(f"{msg['agent_name']}: {msg['content']}")
        else:
            processed_messages.append(f"{msg['role']}: {msg['content']}")
    conversation_text = "\n".join(processed_messages)

    prompt = make_agent_decider_prompt_flow(conversation_text, all_agents=all_agents)

    response = client.beta.chat.completions.parse(
        model=config.get("models.dicision"),
        messages=[{"role": "system", "content": prompt}],
        response_format=FlowAgentSchema
    )
    content = response.choices[0].message.parsed
    if not content:
        return {"next_agent": ""}
    return extract_json_content(content)

