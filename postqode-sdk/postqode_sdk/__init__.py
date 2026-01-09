"""
PostQode Agent SDK
==================

SDK for building agents that integrate with the PostQode Marketplace.
Provides health reporting, configuration management, and invocation tracking.

Usage:
    from postqode_sdk import PostQodeAgent, AgentConfig
    
    agent = PostQodeAgent()
    
    @agent.on_invoke
    def handle_request(input_data):
        # Your agent logic here
        return {"result": "processed"}
    
    if __name__ == "__main__":
        agent.run()
"""

from .agent import PostQodeAgent
from .config import AgentConfig
from .health import HealthReporter
from .decorators import on_invoke, on_startup, on_shutdown

__version__ = "0.1.0"
__all__ = [
    "PostQodeAgent",
    "AgentConfig", 
    "HealthReporter",
    "on_invoke",
    "on_startup",
    "on_shutdown"
]
