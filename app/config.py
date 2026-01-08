"""
Configuration settings for MOPS Financial API
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""
    model_config = SettingsConfigDict(env_prefix="MOPS_")
    
    # Request settings
    request_timeout: float = 30.0
    max_retries: int = 3
    
    # Database settings
    database_url: str = "postgresql+asyncpg://postgres:postgres@core-postgres:5432/mops_financial_db"


settings = Settings()

