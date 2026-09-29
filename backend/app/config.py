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
    # Segredo do app na Meta: confere a assinatura de cada chamada do
    # webhook. Vazio = nenhuma chamada é aceita (falha fechada).
    whatsapp_app_secret: str = ""
    # Senha combinada com a Meta no cadastro do webhook (o desafio GET).
    whatsapp_verify_token: str = ""
    whatsapp_api_version: str = "v25.0"
    # Endereço público do túnel (ex.: algo.ngrok-free.dev). Por ele, só
    # as rotas /webhook/ passam; o resto da API fica só na máquina.
    public_webhook_host: str = ""
    # Espera antes de responder no WhatsApp, recomeçada a cada mensagem
    # nova, para juntar mensagens quebradas numa resposta só. A triagem
    # não espera.
    reply_debounce_seconds: float = 6.0
    # Conta de e-mail do produto que envia os alertas para as
    # profissionais (uma só para todas; cada profissional só informa o
    # endereço onde recebe). Sem `smtp_host`, o envio é registrado como
    # falha na trilha do alerta.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    # Login com o Google (só identidade: nome, e-mail e foto). O Client ID
    # não é segredo; vai para o navegador pelo `GET /auth/config`.
    google_client_id: str = ""
    # Segredo do mesmo cliente OAuth. Só a agenda usa: trocar o código da
    # janela de permissão por um acesso que a MarIA guarda. O login não
    # precisa dele. Vazio = o botão "Sincronizar" fica desligado.
    google_client_secret: str = ""
    # Fuso em que o horário de atendimento é lido e os horários são
    # oferecidos.
    agenda_timezone: str = "America/Sao_Paulo"
    # E-mails que podem entrar no painel, separados por vírgula. Vazio =
    # ninguém entra (falha fechada): no MVP a MarIA é só para convidados.
    allowed_emails: str = ""
    session_days: int = 7
    # Ligar em produção (HTTPS). Em desenvolvimento o painel roda em
    # http://localhost e um cookie `Secure` não seria enviado.
    session_cookie_secure: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
