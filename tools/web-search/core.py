from duckduckgo_search import DDGS
from ultraconfiguration import UltraConfig
import os
from .decision import query_finder

#! Initialize ---------------------------------------------------------------
config_path = os.path.join(os.path.dirname(__file__), "config.json")
config = UltraConfig(config_path)

#* Web search ---------------------------------------------------------------
def web_search(message: str) -> dict:
    """Perform web search using DuckDuckGo"""
    try:
        querys = query_finder(message).get("query", "")
        if not querys:
            return {"text": "", "data": {"queries": [], "results": []}}
        
        formatted_results = []
        structured_results = []
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
                    structured_results.append({
                        "url": r["href"],
                        "title": r["title"],
                        "snippet": r["body"]
                    })
        text_output = "\n---\n".join(formatted_results) if formatted_results else ""
        return {
            "text": text_output,
            "data": {
                "queries": querys,
                "results": structured_results
            }
        }
    except Exception as e:
        return {"text": "", "data": {"queries": [], "results": []}}