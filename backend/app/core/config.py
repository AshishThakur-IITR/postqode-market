from pydantic_settings import BaseSettings
from typing import List, Union

class Settings(BaseSettings):
    PROJECT_NAME: str = "postqode"
    API_V1_STR: str = "/api/v1"
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000", "http://localhost:5173"]
    
    DATABASE_URL: str = "postgresql://user:password@localhost/postqode_db"
    
    # JWT Authentication Settings
    SECRET_KEY: str = "your-secret-key-change-in-production"  # IMPORTANT: Change in production!
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    AGENT_TOKEN_EXPIRE_HOURS: int = 24  # Agent tokens valid for 24 hours
    
    # OIDC/OAuth Settings (for future federation)
    OIDC_ISSUER: str = ""
    OIDC_CLIENT_ID: str = ""
    OIDC_CLIENT_SECRET: str = ""

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
