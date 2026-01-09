"""
PostQode Agent - Main agent class.
Provides HTTP server and integration with marketplace.
"""
import asyncio
import signal
import logging
from typing import Callable, Dict, Any, Optional, List
from contextlib import asynccontextmanager

from .config import AgentConfig
from .health import HealthReporter, AsyncHealthReporter
from .decorators import get_invoke_handlers, get_startup_handlers, get_shutdown_handlers

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    import uvicorn
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

logger = logging.getLogger("postqode.agent")


class InvokeRequest(BaseModel):
    """Request model for agent invocation."""
    input: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None


class InvokeResponse(BaseModel):
    """Response model for agent invocation."""
    output: Any
    metadata: Optional[Dict[str, Any]] = None


class PostQodeAgent:
    """
    Main PostQode Agent class.
    
    Provides:
    - HTTP server for receiving invocations
    - Health reporting to marketplace
    - Configuration management
    - Adapter integration
    
    Usage:
        from postqode_sdk import PostQodeAgent
        
        agent = PostQodeAgent()
        
        @agent.invoke
        def handle(input_data):
            return {"result": input_data}
        
        agent.run()
    """
    
    def __init__(self, config: Optional[AgentConfig] = None):
        """
        Initialize the agent.
        
        Args:
            config: Optional AgentConfig. If not provided, reads from env.
        """
        self.config = config or AgentConfig.from_env()
        self._invoke_handler: Optional[Callable] = None
        self._startup_handlers: List[Callable] = []
        self._shutdown_handlers: List[Callable] = []
        self._health_reporter: Optional[HealthReporter] = None
        self._app: Optional["FastAPI"] = None
        
        logger.info(f"PostQode Agent initialized")
        logger.info(f"  Deployment ID: {self.config.deployment_id}")
        logger.info(f"  Agent ID: {self.config.agent_id}")
        logger.info(f"  Adapter: {self.config.adapter}")
        logger.info(f"  Marketplace: {self.config.marketplace_url}")
    
    def invoke(self, func: Callable) -> Callable:
        """
        Decorator to set the invoke handler.
        
        Args:
            func: Handler function that takes input_data and returns output
        """
        self._invoke_handler = func
        return func
    
    def on_startup(self, func: Callable) -> Callable:
        """Decorator to register startup handler."""
        self._startup_handlers.append(func)
        return func
    
    def on_shutdown(self, func: Callable) -> Callable:
        """Decorator to register shutdown handler."""
        self._shutdown_handlers.append(func)
        return func
    
    def _build_app(self) -> "FastAPI":
        """Build the FastAPI application."""
        if not HAS_FASTAPI:
            raise ImportError("FastAPI and uvicorn required. Install with: pip install fastapi uvicorn")
        
        agent = self  # Capture for closure
        
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            logger.info("Agent starting...")
            
            # Run startup handlers
            for handler in self._startup_handlers:
                handler()
            for handler in get_startup_handlers():
                handler()
            
            # Start health reporter
            self._health_reporter = HealthReporter(
                deployment_id=self.config.deployment_id,
                marketplace_url=self.config.marketplace_url,
                interval=self.config.health_interval
            )
            self._health_reporter.start()
            
            yield
            
            # Shutdown
            logger.info("Agent shutting down...")
            
            if self._health_reporter:
                self._health_reporter.stop()
            
            for handler in self._shutdown_handlers:
                handler()
            for handler in get_shutdown_handlers():
                handler()
        
        app = FastAPI(
            title=f"PostQode Agent - {self.config.agent_id}",
            description="PostQode Marketplace Agent",
            version="1.0.0",
            lifespan=lifespan
        )
        
        @app.get("/health")
        def health_check():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "agent_id": agent.config.agent_id,
                "deployment_id": agent.config.deployment_id,
                "adapter": agent.config.adapter,
                "invocations": agent._health_reporter.invocation_count if agent._health_reporter else 0
            }
        
        @app.post("/invoke", response_model=InvokeResponse)
        def invoke_agent(request: InvokeRequest):
            """
            Invoke the agent with input data.
            
            Args:
                request: InvokeRequest with input and optional context
                
            Returns:
                InvokeResponse with output
            """
            # Get handler
            handler = agent._invoke_handler
            if not handler:
                # Try decorated handlers
                handlers = get_invoke_handlers()
                if handlers:
                    handler = handlers[0]
            
            if not handler:
                raise HTTPException(status_code=500, detail="No invoke handler registered")
            
            try:
                # Record invocation
                if agent._health_reporter:
                    agent._health_reporter.record_invocation()
                
                # Call handler
                result = handler(request.input)
                
                return InvokeResponse(output=result)
                
            except Exception as e:
                logger.error(f"Invoke error: {e}")
                if agent._health_reporter:
                    agent._health_reporter.record_error(str(e))
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.get("/config")
        def get_config():
            """Get agent configuration (non-sensitive)."""
            return {
                "agent_id": agent.config.agent_id,
                "adapter": agent.config.adapter,
                "custom_config": agent.config.custom_config
            }
        
        return app
    
    def run(self, host: str = "0.0.0.0", port: Optional[int] = None):
        """
        Run the agent server.
        
        Args:
            host: Host to bind to
            port: Port to listen on (default from config)
        """
        if not HAS_FASTAPI:
            raise ImportError("FastAPI and uvicorn required")
        
        port = port or self.config.port
        
        self._app = self._build_app()
        
        logger.info(f"Starting agent server on {host}:{port}")
        
        uvicorn.run(
            self._app,
            host=host,
            port=port,
            log_level="info"
        )
    
    async def run_async(self, host: str = "0.0.0.0", port: Optional[int] = None):
        """Run the agent server asynchronously."""
        if not HAS_FASTAPI:
            raise ImportError("FastAPI and uvicorn required")
        
        port = port or self.config.port
        self._app = self._build_app()
        
        config = uvicorn.Config(self._app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
