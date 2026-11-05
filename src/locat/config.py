"""Central settings for Loca-T, loaded from the .env file."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Loca-T"
    environment: str = "development"
    database_url: str = "sqlite:///./locat.db"

    at_username: str = "sandbox"
    at_api_key: str = ""
    at_sender_id: str = ""

    public_base_url: str = ""

    # "console" prints SMS in the server terminal; "africastalking" really sends.
    sms_mode: str = "console"
    # Share of each booking's total that goes to the community fund.
    community_fund_rate: float = 0.05

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()