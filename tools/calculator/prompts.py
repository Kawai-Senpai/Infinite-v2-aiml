def make_query(message: str) -> str:
    example = """Your output should look like this (example):
{
    "add": [2.0, 3.0, 5.1],
    "sub": [10.0, 5.1, 5.2],
    "mul": [2.5, 3.7, 6.1],
    "div": [10.7, 2.9, 5.8]
}
"""
    return f"""This is a user message. Come up a output like the given example and the calculator will return the result.
This is a calculator tool. Analyze if this user message requires any calculations. And come up with the numbers to calculate.

Message: "{message}"

{example}

Rules:
- It is not mandetory to use all the operations. If nothing is needed, return empty array.
- The calculation query should be able to help the chatbot/user answer the question.
"""