from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.api_v1.api import api_router
from .core.config import settings
from .db.base import Base
from .db.session import engine

# Create tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="postqode API",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
)

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def root():
    return {"message": "Welcome to postqode API"}
