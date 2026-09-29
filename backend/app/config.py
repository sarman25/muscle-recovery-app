from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    bot_token: str = "temporary_placeholder"
    database_url: str = "sqlite+aiosqlite:///./app.db"
    secret_key: str = "temporary_placeholder"
    environment: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()