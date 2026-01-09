"""
Hello Agent - PostQode Sample Agent

A simple demo agent that demonstrates the PostQode SDK.
Echoes messages back with optional transformations.
"""
from datetime import datetime
from postqode_sdk import PostQodeAgent

# Create agent
agent = PostQodeAgent()


@agent.on_startup
def initialize():
    """Called when agent starts."""
    print("=" * 50)
    print("🚀 Hello Agent Starting!")
    print(f"   Deployment ID: {agent.config.deployment_id}")
    print(f"   Adapter: {agent.config.adapter}")
    print("=" * 50)


@agent.invoke
def handle_request(input_data: dict) -> dict:
    """
    Main handler for agent invocations.
    
    Args:
        input_data: Dict with 'message' and optional 'uppercase'
        
    Returns:
        Dict with 'response' and 'timestamp'
    """
    message = input_data.get("message", "Hello!")
    uppercase = input_data.get("uppercase", False)
    
    # Process message
    greeting = agent.config.get("greeting", "Hello from PostQode!")
    response = f"{greeting} You said: {message}"
    
    if uppercase:
        response = response.upper()
    
    return {
        "response": response,
        "timestamp": datetime.utcnow().isoformat(),
        "agent_id": agent.config.agent_id,
        "adapter": agent.config.adapter
    }


@agent.on_shutdown
def cleanup():
    """Called when agent shuts down."""
    print("👋 Hello Agent shutting down...")


# Run agent
if __name__ == "__main__":
    agent.run()
