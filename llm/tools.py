from ultraconfiguration import UltraConfig
from ultraprint.logging import logger
from keys.keys import environment
import importlib
from llm.decision import analyze_tool_need
from concurrent.futures import ThreadPoolExecutor, as_completed

#! Initialize ---------------------------------------------------------------
config = UltraConfig('config.json')
log = logger('chat_log', 
            filename='debug/chat.log', 
            include_extra_info=config.get("logging.include_extra_info", False), 
            write_to_file=config.get("logging.write_to_file", False), 
            log_level=config.get("logging.development_level", "DEBUG") if environment == 'development' else config.get("logging.production_level", "INFO"))

#* Executor ------------------------------------------------------------------
def _execute_tool(tool, agent, message, history):
    """
    Execute a single tool.

    This function dynamically imports and executes a specified tool module.

    Args:
        tool (str): The name of the tool to execute.
        agent (dict): The agent configuration.
        message (str): The user message.
        history (list): The chat history.

    Returns:
        dict: A dictionary containing the tool name and its response.
    """
    try:
        tool_module = importlib.import_module(f"tools.{tool}.main")
        response = tool_module._execute(agent, message, history)
        return {"tool": tool, "response": response}
    except ImportError as e:
        log.error("Could not import or use tool '%s': %s", tool, e)
        return {"tool": tool, "response": f"Error: {str(e)}"}

def execute_tools(agent, message, history):
    """
    Execute multiple tools in parallel and combine their responses.

    This function analyzes the user message to determine which tools are needed,
    executes those tools in parallel, and combines their responses into a single output.

    Args:
        agent (dict): The agent configuration, including enabled tools.
        message (str): The user message.
        history (list): The chat history.

    Returns:
        dict: A dictionary containing the combined text output and metadata from the executed tools.
    """
    try:
        enabled_tools = agent.get("tools", [])
        # Build updated tool descriptions
        updated_tools = []
        for tool in enabled_tools:
            try:
                tool_module = importlib.import_module(f"tools.{tool}.main")
                tool_item = {
                    "name": tool,
                    "description": getattr(tool_module, "_info", "")
                }
            except ImportError as e:
                log.error("Could not import tool '%s' for description: %s", tool, e)
                tool_item = {"name": tool, "description": ""}
            updated_tools.append(tool_item)
        
        response = analyze_tool_need(message, updated_tools)
        tools_list = response.get("tools", [])
        if not tools_list:
            return {"text": "", "metadata": {"results": [], "used": [], "not_used": enabled_tools}}
        
        log.debug("Executing tools in parallel: %s", tools_list)
        max_workers = min(len(tools_list), config.get("constraints.max_parallel_tools", 5))
        responses = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_tool = {
                executor.submit(_execute_tool, tool, agent, message, history): tool 
                for tool in tools_list
            }
            for future in as_completed(future_to_tool):
                result = future.result()
                if result:
                    responses.append(result)

        text_output = "\n\n".join([
            f"{r['tool']} response: {r['response'].get('text', '')}"
            for r in responses
        ])
        metadata_output = [
            {"tool": r["tool"], "metadata": r["response"].get("data", {})}
            for r in responses
        ]
        used = tools_list
        not_used = [tool for tool in [t["name"] for t in updated_tools] if tool not in used]
        return {"text": text_output, "metadata": {"results": metadata_output, "used": used, "not_used": not_used}}
    except Exception as e:
        log.error("Error executing tools: %s", e)
        return {"text": "", "metadata": {"results": [], "used": [], "not_used": []}}
