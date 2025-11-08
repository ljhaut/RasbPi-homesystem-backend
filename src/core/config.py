from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ENTSOE_API_KEY: str
    ENTSOE_API_URL: str
    FINNISH_VAT_PERCENTAGE: float
    DATABASE_URL: str
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: list[str]
    CORS_METHODS: list[str]
    CORS_HEADERS: list[str]

    class Config:
        env_file = ".env"


app_settings = Settings()
