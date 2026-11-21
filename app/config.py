from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_host: str = "0.0.0.0"
    app_port: int = 4000
    request_timeout_seconds: float = 10.0
    simulation_mode: bool = False

    # Platform credentials
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    telegram_channel_username: Optional[str] = None

    discord_webhook_url: Optional[str] = None

    slack_webhook_url: Optional[str] = None

    mastodon_instance_url: str = "https://mastodon.social"
    mastodon_access_token: Optional[str] = None

    devto_api_key: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
