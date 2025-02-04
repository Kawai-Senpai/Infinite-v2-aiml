from duckduckgo_search import DDGS
from ultraconfiguration import UltraConfig
import os

#! Initialize ---------------------------------------------------------------
config_path = os.path.join(os.path.dirname(__file__), "config.json")
config = UltraConfig(config_path)

#* Web search ---------------------------------------------------------------
def web_search(query: str) -> str:
    """Perform web search using DuckDuckGo"""
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=config.get("max_results", 2))
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
        return ""