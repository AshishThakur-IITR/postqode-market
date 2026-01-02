from fastapi import APIRouter
from .endpoints import market, chat, organizations, auth, agent_auth, admin, packages, deployments

api_router = APIRouter()

# Authentication routes
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(agent_auth.router, prefix="/agent-auth", tags=["agent-auth"])

# Application routes
api_router.include_router(market.router, prefix="/market", tags=["market"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])

# Package & Deployment routes
api_router.include_router(packages.router, prefix="/market", tags=["packages"])
api_router.include_router(deployments.router, prefix="/deployments", tags=["deployments"])

# Admin routes
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])

