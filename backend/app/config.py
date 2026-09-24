from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@localhost:5432/chatbot_tcc"
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-5"
    # Modelo da camada 2 da triagem. Fica fixo e separado do modelo da
    # conversa: trocar o modelo que responde não pode mudar, sem querer,
    # quem decide o que é emergência.
    triage_model: str = "claude-opus-5"
    triage_timeout_seconds: float = 20.0
    chroma_persist_dir: str = "./chroma_data"
    frontend_url: str = "http://localhost:5173"
    data_encryption_key: str = ""
    data_retention_days: int = 90
    whatsapp_access_token: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
