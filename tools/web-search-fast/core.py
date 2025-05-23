from duckduckgo_search import DDGS
from ultraconfiguration import UltraConfig
import os

#! Initialize ---------------------------------------------------------------
config_path = os.path.join(os.path.dirname(__file__), "config.json")
config = UltraConfig(config_path)

#* Web search ---------------------------------------------------------------
def web_search(query: str) -> dict:
    """Perform web search using DuckDuckGo"""
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=config.get("max_results", 2))
            if not results:
                return {
                    "text": "No search results found.",
                    "data": {
                        "query": query,
                        "results": []
                    }
                }
            
            formatted_results = []
            structured_results = []
            for r in results:
                formatted_results.append(
                    f"Title: {r['title']}\n"
                    f"URL: {r['href']}\n"
                    f"Summary: {r['body']}\n"
                )
                structured_results.append({
                    "url": r["href"],
                    "title": r["title"],
                    "snippet": r["body"]
                })
            text_output = "\n---\n".join(formatted_results)
            return {
                "text": text_output,
                "data": {
                    "query": query,
                    "results": structured_results
                }
            }
    except Exception as e:
        return {
            "text": "",
            "data": {
                "query": query,
                "results": []
            }
        }