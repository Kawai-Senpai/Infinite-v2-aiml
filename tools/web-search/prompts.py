
def make_query(message: str) -> str:
    """Format prompt for tool analysis"""
    example = """Your output should look like this (example):
{
    "query": ["search query1", "search query2"]
}"""
    return f"""This is a user message. come up with a search query based on the message. so that the search query can be used to search the web.

Message: "{message}"

{example}

Rules:
- Only include the search query under "query" that is needed to respond to the message.
- The search query should be relevant to the message. And help to find the information that the user is looking for.
"""