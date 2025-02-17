from llm.agents import create_agent
from llm.sessions import create_team_session
from llm.chat import team_chat_flow as team_chat

def create_test_agents():
    """Create three test agents with different roles"""
    
    # Create a scientist agent
    scientist = create_agent(
        name="Scientist",
        capabilities=["Scientific analysis", "Data interpretation", "Research methodology"],
        rules=["Always cite evidence", "Be precise", "Consider multiple hypotheses"],
        model_provider="openai",
        model="gpt-4o",
        agent_type="public",
        tools=["web-search", "calculator"]
    )
    
    # Create a creative writer
    writer = create_agent(
        name="Creative Writer",
        role="You are a creative writer who thinks outside the box",
        capabilities=["Creative thinking", "Storytelling", "Unique perspectives"],
        rules=["Be imaginative", "Use metaphors", "Think unconventionally"],
        model_provider="openai",
        model="gpt-4o",
        agent_type="public",
        tools=["web-search"]
    )
    
    # Create a pragmatic advisor
    advisor = create_agent(
        name="Pragmatic Advisor",
        role="You are a practical advisor who focuses on feasible solutions",
        capabilities=["Problem-solving", "Risk assessment", "Practical planning"],
        rules=["Focus on practicality", "Consider constraints", "Suggest actionable steps"],
        model_provider="openai",
        model="gpt-4o",
        agent_type="public",
        tools=["web-search","calculator"]
    )
    
    return scientist, writer, advisor

def test_team_chat():
    """Test the team chat functionality in both streaming and non-streaming modes."""
    try:
        # Create the agents
        print("Creating agents...")
        scientist_id, writer_id, advisor_id = create_test_agents()
        print(f"Created agents: {scientist_id, writer_id, advisor_id}")
        
        # Create a team session
        print("\nCreating team session...")
        session_id = create_team_session(
            agent_ids=[scientist_id, writer_id, advisor_id],
            max_context_results=1
        )
        print(f"Created team session: {session_id}")
        
        # Define a test question
        question = "discuss among yourselves the meaning of life for a long time"
        print(f"\nQuestion: {question}")
        print("-" * 50)
        
        # Test streaming response
        print("\nStreaming team responses:")
        stream_response = team_chat(
            session_id=session_id,
            message=question,
            stream=True,
            use_rag=True,
            include_rich_response=True
        )
        for chunk in stream_response:
            print(chunk, end="")
        print("\n" + "-" * 50)
        
        # Test non-streaming response
        print("\nNon-streaming team response:")
        non_stream_response = team_chat(
            session_id=session_id,
            message=question,
            stream=False,
            use_rag=True,
            include_rich_response=True
        )
        # non_stream_response is a dictionary with aggregated conversation
        print(non_stream_response.get("conversation"))
        print("\n" + "-" * 50)
        
    except Exception as e:
        print(f"Error in test: {str(e)}")

if __name__ == "__main__":
    test_team_chat()
