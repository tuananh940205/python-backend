from pydantic_settings import SettingsConfigDict, BaseSettings

# BaseSettings sẽ đọc biến DATABASE_URL trong .env và ánh xạ thành settings.database_url.
class Settings(BaseSettings):
    database_url: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()