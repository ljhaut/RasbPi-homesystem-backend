from pathlib import Path

from dotenv import dotenv_values
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PICO1_PATH: str | None = None
    PICO2_PATH: str | None = None
    ENTSOE_API_KEY: str
    ENTSOE_API_URL: str
    FINNISH_VAT_PERCENTAGE: float
    DATABASE_URL: str
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: list[str]
    CORS_METHODS: list[str]
    CORS_HEADERS: list[str]
    CAR_CHARGE_THRESHOLD_C: float = 8.0

    class Config:
        env_file = ".env"


app_settings = Settings()

PICO_ENV_PATH = Path("/workspace/pico_sim.env")
if PICO_ENV_PATH.exists():
    pico_env = dotenv_values(PICO_ENV_PATH)
    app_settings.PICO1_PATH = pico_env.get("PICO1_PATH", app_settings.PICO1_PATH)
    app_settings.PICO2_PATH = pico_env.get("PICO2_PATH", app_settings.PICO2_PATH)
