from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@localhost:5432/chatbot_tcc"
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-5"
    chroma_persist_dir: str = "./chroma_data"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
