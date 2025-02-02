from duckduckgo_search import DDGS
from ultraconfiguration import UltraConfig
from ultraprint.logging import logger
from keys.keys import environment

#! Initialize ---------------------------------------------------------------
config = UltraConfig('config.json')
log = logger('chat_log', 
            filename='debug/chat.log', 
            include_extra_info=config.get("logging.include_extra_info", False), 
            write_to_file=config.get("logging.write_to_file", False), 
            log_level=config.get("logging.development_level", "DEBUG") if environment == 'development' else config.get("logging.production_level", "INFO"))

#* Executor ------------------------------------------------------------------
def execute_tools(tools_list: list) -> str:
    """Execute multiple tools and combine their responses"""
    if not tools_list:
        return ""
    
    responses = []
    for tool in tools_list:
        tool_name = tool["name"]
        query = tool["query"]
        
        if tool_name == "web-search":
            response = web_search(query)
            responses.append({
                "tool": tool_name,
                "response": response
            })
        #TODO: Add more tool handlers here

    return "\n\n".join([f"{r['tool']} response: {r['response']}" for r in responses])

#* Tool Handlers -------------------------------------------------------------
def web_search(query: str) -> str:
    """Perform web search using DuckDuckGo"""
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=config.get("constraints.max_search_results", 2))
            if not results:
                return "No search results found."
            
            formatted_results = []
            for r in results:
                formatted_results.append(
                    f"Title: {r['title']}\n"
                    f"URL: {r['href']}\n"
                    f"Summary: {r['body']}\n"
                )
            
            return "\n---\n".join(formatted_results)
    except Exception as e:
        return f"Error performing web search: {str(e)}"
