from .core import web_search

#? Required ------------------------------------------------------------------
_info = "This tool allows you to perform web searches using DuckDuckGo. But the query is generated automatically based on the user message using an LLM."
_author = "Ranit"
_group = "InfiniteRegen"
_type = "official" #available types are: official, thirdparty

def _execute(agent, message, history):
    """Main function to execute the web search tool"""
    try:
        return web_search(message)
    except Exception as e:
        return {"text": "", "data": {"queries": [], "results": []}}