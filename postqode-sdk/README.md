# PostQode Agent SDK

SDK for building agents that integrate with the PostQode Marketplace.

## Installation

```bash
pip install postqode-sdk[server]
```

## Quick Start

Create an agent in `agent.py`:

```python
from postqode_sdk import PostQodeAgent

# Create agent instance
agent = PostQodeAgent()

# Define your invoke handler
@agent.invoke
def handle_request(input_data):
    """
    Process incoming requests.
    
    Args:
        input_data: Dict with input from the caller
        
    Returns:
        Dict with your response
    """
    message = input_data.get("message", "Hello")
    return {
        "response": f"Agent received: {message}",
        "processed": True
    }

# Optional: startup handler
@agent.on_startup
def initialize():
    print("Agent is starting...")

# Optional: shutdown handler  
@agent.on_shutdown
def cleanup():
    print("Agent is shutting down...")

# Run the agent
if __name__ == "__main__":
    agent.run()
```

## Environment Variables

The SDK reads these environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTQODE_DEPLOYMENT_ID` | Deployment ID for tracking | `local-dev` |
| `POSTQODE_AGENT_ID` | Your agent's ID | `unknown` |
| `POSTQODE_ADAPTER` | Runtime adapter (openai, anthropic, etc.) | `openai` |
| `POSTQODE_MARKETPLACE_URL` | Marketplace API URL | `http://localhost:8000` |
| `POSTQODE_AGENT_PORT` | Port to run on | `8080` |
| `POSTQODE_HEALTH_INTERVAL` | Seconds between health pings | `30` |

## API Endpoints

When running, your agent exposes:

- `GET /health` - Health check endpoint
- `POST /invoke` - Invoke the agent
- `GET /config` - Get agent configuration

### Invoke Example

```bash
curl -X POST http://localhost:8080/invoke \
  -H "Content-Type: application/json" \
  -d '{"input": {"message": "Hello agent!"}}'
```

Response:
```json
{
  "output": {
    "response": "Agent received: Hello agent!",
    "processed": true
  }
}
```

## Health Reporting

The SDK automatically sends health pings to the PostQode Marketplace every 30 seconds (configurable). This includes:

- Invocation count
- Last invocation time
- Status updates

## Creating a Package

Your agent package structure:

```
my-agent/
├── manifest.yaml      # Required: agent metadata
├── agent.py           # Required: main entry point
├── requirements.txt   # Optional: dependencies
└── Dockerfile         # Optional: custom container config
```

### manifest.yaml

```yaml
apiVersion: postqode.io/v1
kind: Agent
metadata:
  name: my-agent
  version: 1.0.0
spec:
  runtime:
    minVersion: "1.0.0"
  adapters:
    - openai
    - anthropic
```

## License

MIT
