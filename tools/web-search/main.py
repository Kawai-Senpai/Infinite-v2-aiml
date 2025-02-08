from .core import web_search

#? Required ------------------------------------------------------------------
_info = "This tool allows you to perform web searches using DuckDuckGo. But the query is generated automatically based on the user message using an LLM."

def _execute(agent, message, history):
    """Main function to execute the web search tool"""
    return web_search(message)