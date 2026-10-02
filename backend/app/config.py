from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "postgresql+psycopg://bedayti:bedayti@localhost:5432/bedayti"
    upload_dir: str = "./uploads"
    max_upload_mb: int = 50
    default_currency: str = "EGP"
    allow_self_approval: bool = True  # single-user mode; set false once several users exist
    api_tokens: str = ""  # "token:role[:name],..." roles: viewer|analyst|admin
    fiscal_year_start_month: int = 1  # 1 = calendar year; 7 = July–June named by end year


@lru_cache
def get_settings() -> Settings:
    return Settings()
