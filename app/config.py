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
    
    # Database settings - 分離變數，和 docker-compose POSTGRES_* 對齊
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_host: str = "core-postgres"
    postgres_port: int = 5432
    postgres_db: str = "mops_financial_db"
    
    @property
    def database_url(self) -> str:
        """組合成 SQLAlchemy 連接字串"""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
