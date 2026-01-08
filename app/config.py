"""
Configuration settings for MOPS Financial API
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Request settings
    request_timeout: float = 30.0
    max_retries: int = 3
    
    # Database settings
    database_url: str = "postgresql+asyncpg://postgres:postgres@core-postgres:5432/mops_financial_db"
    
    class Config:
        env_prefix = "MOPS_"


settings = Settings()
