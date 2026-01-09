"""
Health Reporter.
Sends health pings and invocation stats to the marketplace.
"""
import asyncio
import httpx
import logging
from datetime import datetime
from typing import Optional
from threading import Thread
import time

logger = logging.getLogger("postqode.health")


class HealthReporter:
    """
    Reports agent health status to PostQode Marketplace.
    Runs in background thread, sends periodic health pings.
    """
    
    def __init__(
        self,
        deployment_id: str,
        marketplace_url: str,
        interval: int = 30
    ):
        self.deployment_id = deployment_id
        self.marketplace_url = marketplace_url.rstrip("/")
        self.interval = interval
        
        self._running = False
        self._thread: Optional[Thread] = None
        self._total_invocations = 0
        self._last_invocation: Optional[datetime] = None
        self._last_error: Optional[str] = None
    
    def start(self):
        """Start the health reporter background thread."""
        if self._running:
            return
        
        self._running = True
        self._thread = Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info(f"Health reporter started (interval: {self.interval}s)")
    
    def stop(self):
        """Stop the health reporter."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Health reporter stopped")
    
    def record_invocation(self):
        """Record an agent invocation."""
        self._total_invocations += 1
        self._last_invocation = datetime.utcnow()
    
    def record_error(self, error: str):
        """Record an error."""
        self._last_error = error
    
    def _run_loop(self):
        """Background loop that sends health pings."""
        while self._running:
            try:
                self._send_health_ping()
            except Exception as e:
                logger.error(f"Health ping failed: {e}")
            
            # Sleep for interval
            time.sleep(self.interval)
    
    def _send_health_ping(self):
        """Send a health ping to the marketplace."""
        url = f"{self.marketplace_url}/api/v1/deployments/{self.deployment_id}/health"
        
        payload = {
            "total_invocations": self._total_invocations,
            "last_invocation": self._last_invocation.isoformat() if self._last_invocation else None,
        }
        
        try:
            with httpx.Client(timeout=10) as client:
                response = client.post(url, json=payload)
                
                if response.status_code == 200:
                    logger.debug(f"Health ping sent: {self._total_invocations} invocations")
                else:
                    logger.warning(f"Health ping returned {response.status_code}: {response.text}")
        except httpx.RequestError as e:
            logger.warning(f"Could not reach marketplace: {e}")
    
    @property
    def invocation_count(self) -> int:
        """Get total invocation count."""
        return self._total_invocations


class AsyncHealthReporter:
    """
    Async version of health reporter for async agents.
    """
    
    def __init__(
        self,
        deployment_id: str,
        marketplace_url: str,
        interval: int = 30
    ):
        self.deployment_id = deployment_id
        self.marketplace_url = marketplace_url.rstrip("/")
        self.interval = interval
        
        self._task: Optional[asyncio.Task] = None
        self._total_invocations = 0
        self._last_invocation: Optional[datetime] = None
    
    async def start(self):
        """Start the async health reporter."""
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"Async health reporter started (interval: {self.interval}s)")
    
    async def stop(self):
        """Stop the async health reporter."""
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Async health reporter stopped")
    
    def record_invocation(self):
        """Record an invocation."""
        self._total_invocations += 1
        self._last_invocation = datetime.utcnow()
    
    async def _run_loop(self):
        """Async loop for health pings."""
        while True:
            try:
                await self._send_health_ping()
            except Exception as e:
                logger.error(f"Health ping failed: {e}")
            
            await asyncio.sleep(self.interval)
    
    async def _send_health_ping(self):
        """Send async health ping."""
        url = f"{self.marketplace_url}/api/v1/deployments/{self.deployment_id}/health"
        
        payload = {
            "total_invocations": self._total_invocations,
            "last_invocation": self._last_invocation.isoformat() if self._last_invocation else None,
        }
        
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, json=payload)
            
            if response.status_code == 200:
                logger.debug(f"Health ping sent: {self._total_invocations} invocations")
