"""Non-credential runtime configuration.

Credentials never live here -- they arrive per request in HTTP headers
(see middleware.py) and are never read from the environment.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    mcp_http_host: str = "0.0.0.0"
    mcp_http_port: int = 8080
    do_base_url: str = "https://api.digitalocean.com"


def load_settings() -> Settings:
    return Settings()
