"""
Agent decorators for defining handlers.
"""
from functools import wraps
from typing import Callable, Any

# Storage for decorated handlers
_invoke_handlers = []
_startup_handlers = []
_shutdown_handlers = []


def on_invoke(func: Callable) -> Callable:
    """
    Decorator to register an invoke handler.
    
    Usage:
        @on_invoke
        def handle_request(input_data):
            return {"result": "processed"}
    """
    _invoke_handlers.append(func)
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    
    return wrapper


def on_startup(func: Callable) -> Callable:
    """
    Decorator to register a startup handler.
    Called when agent starts.
    
    Usage:
        @on_startup
        def initialize():
            print("Agent starting...")
    """
    _startup_handlers.append(func)
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    
    return wrapper


def on_shutdown(func: Callable) -> Callable:
    """
    Decorator to register a shutdown handler.
    Called when agent stops.
    
    Usage:
        @on_shutdown
        def cleanup():
            print("Agent shutting down...")
    """
    _shutdown_handlers.append(func)
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    
    return wrapper


def get_invoke_handlers():
    """Get all registered invoke handlers."""
    return _invoke_handlers


def get_startup_handlers():
    """Get all registered startup handlers."""
    return _startup_handlers


def get_shutdown_handlers():
    """Get all registered shutdown handlers."""
    return _shutdown_handlers
