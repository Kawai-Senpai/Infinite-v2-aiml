from duckduckgo_search import DDGS
from ultraconfiguration import UltraConfig
import os
from .decision import query_finder

#! Initialize ---------------------------------------------------------------
config_path = os.path.join(os.path.dirname(__file__), "config.json")
config = UltraConfig(config_path)

#* Web search ---------------------------------------------------------------
def web_search(message: str) -> str:
    """Perform web search using DuckDuckGo"""
    try:
        querys = query_finder(message).get("query", "")
        if not querys:
            return ""
        
        formatted_results = []
        for query in querys:
            with DDGS() as ddgs:
                results = ddgs.text(query, max_results=config.get("max_results", 2))
                if not results:
                    continue
                for r in results:
                    formatted_results.append(
                        f"Title: {r['title']}\n"
                        f"URL: {r['href']}\n"
                        f"Summary: {r['body']}\n"
                    )
        return "\n---\n".join(formatted_results) if formatted_results else ""
    except Exception as e:
        return ""