import re
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.services import guidelines


class VoiceExample(BaseModel):
    good: str = ""
    bad: str = ""


_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

Weekday = Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


class TimeRange(BaseModel):
    """Um intervalo de atendimento num dia, ex.: 10:00 às 16:00."""

    start: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    end: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")

    @model_validator(mode="after")
    def start_before_end(self):
        if self.start >= self.end:
            raise ValueError("O horário de início precisa ser antes do fim")
        return self


class _AssistantProfile(BaseModel):
    """Campos do perfil que a profissional preenche para calibrar a SelenIA."""

    alert_email: Optional[str] = Field(default=None, max_length=255)
    audience_description: Optional[str] = None
    service_info: Optional[str] = None
    voice_examples: Optional[dict[str, VoiceExample]] = None
    extra_never_say: Optional[list[str]] = Field(default=None, max_length=30)
    session_minutes: Optional[int] = Field(default=None, ge=15, le=240)
    pronouns: Optional[Literal["feminine", "masculine", "neutral"]] = None
    # Dias e horários em que atende. Até 3 intervalos por dia (ex.: manhã
    # e tarde, com almoço no meio).
    working_hours: Optional[dict[Weekday, list[TimeRange]]] = None
    # Limite de sessões por dia que a SelenIA pode marcar. Nulo = sem limite.
    max_sessions_per_day: Optional[int] = Field(default=None, ge=1, le=20)
    # Chaves de `guidelines.PAYMENT_METHODS`, sem repetir.
    payment_methods: Optional[list[str]] = Field(default=None, max_length=len(guidelines.PAYMENT_METHODS))

    @field_validator("payment_methods")
    @classmethod
    def only_known_payment_methods(cls, value):
        if value is None:
            return value
        unknown = set(value) - set(guidelines.PAYMENT_METHODS)
        if unknown:
            raise ValueError(f"Forma de pagamento desconhecida: {', '.join(sorted(unknown))}")
        # Na ordem da lista do produto, sem repetir.
        return [key for key in guidelines.PAYMENT_METHODS if key in value]

    @field_validator("working_hours")
    @classmethod
    def no_overlapping_ranges(cls, value):
        if value is None:
            return value
        for ranges in value.values():
            if len(ranges) > 3:
                raise ValueError("No máximo 3 intervalos por dia")
            ordered = sorted(ranges, key=lambda r: r.start)
            if any(a.end > b.start for a, b in zip(ordered, ordered[1:])):
                raise ValueError("Os intervalos de um mesmo dia não podem se sobrepor")
        return value

    @field_validator("alert_email")
    @classmethod
    def valid_email(cls, value):
        if value is None:
            return value
        value = value.strip()
        if not value:
            return None  # campo apagado no painel
        if not _EMAIL.match(value):
            raise ValueError("E-mail inválido")
        return value

    @field_validator("voice_examples")
    @classmethod
    def only_known_questions(cls, value):
        if value is None:
            return value
        unknown = set(value) - guidelines.VOICE_QUESTION_KEYS
        if unknown:
            raise ValueError(f"Pergunta desconhecida: {', '.join(sorted(unknown))}")
        return value

    @field_validator("extra_never_say")
    @classmethod
    def drop_blank_items(cls, value):
        if value is None:
            return value
        return [item.strip() for item in value if item and item.strip()]


class ProfessionalCreate(_AssistantProfile):
    # Sem `slug`, ele é gerado a partir do nome (ex.: "marilia-rossetto").
    slug: Optional[str] = Field(default=None, min_length=3, max_length=64, pattern=r"^[a-z0-9-]+$")
    name: str = Field(min_length=1, max_length=255)
    voice_tone: Optional[str] = None


class ProfessionalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    name: str
    voice_tone: Optional[str] = None
    alert_email: Optional[str] = None
    audience_description: Optional[str] = None
    service_info: Optional[str] = None
    voice_examples: Optional[dict[str, VoiceExample]] = None
    extra_never_say: Optional[list[str]] = None
    # Botão "Em consulta". `in_session_until` nulo com `in_session`
    # verdadeiro = ligado até ela desligar.
    in_session: bool = Field(validation_alias="is_in_session")
    in_session_until: Optional[datetime] = None
    session_minutes: Optional[int] = None
    working_hours: Optional[dict[str, list[TimeRange]]] = None
    max_sessions_per_day: Optional[int] = None
    payment_methods: Optional[list[str]] = None
    pronouns: Optional[str] = None
    onboarding_step: Optional[int] = None
    rules_accepted_at: Optional[datetime] = None
    onboarding_completed_at: Optional[datetime] = None
    created_at: datetime


class WhatsAppStart(BaseModel):
    number: str = Field(max_length=32)
    display_name: str = Field(max_length=100)
    # Como o código chega: SMS ou ligação (para número que não recebe SMS).
    method: str = Field(default="SMS", pattern="^(SMS|VOICE)$")


class WhatsAppResend(BaseModel):
    method: str = Field(default="SMS", pattern="^(SMS|VOICE)$")


class WhatsAppRename(BaseModel):
    display_name: str = Field(max_length=100)


class WhatsAppVerify(BaseModel):
    code: str = Field(max_length=12)


class WhatsAppStatus(BaseModel):
    # O servidor tem a conta da Meta configurada (WABA e token).
    configured: bool
    connected: bool
    # Conexão em andamento: "code_sent" (esperando o código) ou
    # "verified" (falta registrar). Nulo = nada em andamento.
    step: Optional[str] = None
    display_number: Optional[str] = None
    verified_name: Optional[str] = None
    registrations_last_72h: int
    register_limit: int
    # Como a Meta vê o número (ex.: CONNECTED; nome APPROVED ou
    # PENDING_REVIEW). Nulo se a Meta não respondeu.
    meta_status: Optional[str] = None
    name_status: Optional[str] = None
    # Troca de nome pedida: o nome novo e a análise da Meta (PENDING,
    # APPROVED, DECLINED; NONE = nenhuma troca pedida).
    new_display_name: Optional[str] = None
    new_name_status: Optional[str] = None


class InSessionStart(BaseModel):
    # Nulo = até ela desligar. O teto evita ligar "por um dia inteiro" sem querer.
    minutes: Optional[int] = Field(default=None, ge=5, le=240)


class ProfessionalUpdate(_AssistantProfile):
    name: Optional[str] = None
    voice_tone: Optional[str] = None
    # Etapa do cadastro em que ela está, para continuar de onde parou.
    onboarding_step: Optional[int] = Field(default=None, ge=1, le=7)


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    content_type: Optional[str] = None
    chunk_count: int
    uploaded_at: datetime


class ChatRequest(BaseModel):
    professional_slug: str
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    conversation_id: str
    state: str
    # Nulo quando o bot fica em silêncio (profissional no controle ou
    # conversa em espera depois de um alerta).
    reply: Optional[str] = None
    sources: list[str] = []
    disclaimer: Optional[str] = None
    # O que aconteceu por trás da resposta, para o simulador mostrar:
    # nível da triagem ("normal" quando não houve risco), se um alerta
    # foi criado e se a pessoa pediu a profissional ou recusou o bot.
    triage_level: str = "normal"
    alert_created: bool = False
    handoff: Optional[str] = None


class VoiceQuestion(BaseModel):
    key: str
    question: str
    example_good: Optional[str] = None
    example_bad: Optional[str] = None


class PronounOption(BaseModel):
    key: str
    label: str


class PaymentOption(BaseModel):
    key: str
    label: str


class AssistantGuidelines(BaseModel):
    """Regras fixas do produto, exibidas no painel (só leitura)."""

    assistant_name: str
    voice_questions: list[VoiceQuestion]
    never_say: list[str]
    risk_behaviors: list[str]
    pronoun_options: list[PronounOption]
    payment_options: list[PaymentOption]


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    content: str
    sent_by: Optional[str] = None
    delivery_failed: bool = False
    # Foto, áudio ou documento: o painel busca o arquivo em
    # `/conversations/{id}/messages/{message_id}/media`.
    media_type: Optional[str] = None
    media_mime: Optional[str] = None
    media_filename: Optional[str] = None
    created_at: datetime


class LastMessageOut(BaseModel):
    role: str
    sent_by: Optional[str] = None
    # Começo da mensagem, para a lista; a conversa inteira só abrindo.
    preview: str
    created_at: datetime


class AlertBrief(BaseModel):
    level: str
    created_at: datetime


class _ConversationBase(BaseModel):
    id: str
    channel: str
    # Nome do perfil no WhatsApp; sem ele, o número; no simulador, "Conversa de teste".
    contact_name: str
    # Na lista, mascarado (+55 21 •••••-4444); na conversa aberta, completo.
    contact_phone: Optional[str] = None
    state: str
    needs_attention: bool
    awaiting_reply_since: Optional[datetime] = None
    # Tipo do pedido que deixou a conversa aguardando (`models.AwaitingReason`).
    awaiting_reason: Optional[str] = None
    last_message_at: Optional[datetime] = None
    # Janela de 24h do WhatsApp, contada da última mensagem do contato.
    reply_window_closes_at: Optional[datetime] = None
    reply_window_open: bool


class ConversationSummary(_ConversationBase):
    last_message: Optional[LastMessageOut] = None


class ConversationOut(_ConversationBase):
    latest_alert: Optional[AlertBrief] = None
    messages: list[MessageOut] = []


class AlertSummary(BaseModel):
    id: str
    level: str
    trigger_text: Optional[str] = None
    # Trecho que disparou (até 500 caracteres), para entender sem abrir a conversa.
    excerpt: Optional[str] = None
    created_at: datetime
    # "new" ou "reviewed", derivado da trilha.
    status: str
    reviewed_at: Optional[datetime] = None
    conversation_id: str
    conversation_state: str
    channel: str
    contact_name: str
    # Mascarado na lista; completo no alerta aberto.
    contact_phone: Optional[str] = None


class AlertTimelineItem(BaseModel):
    kind: str
    title: str
    detail: Optional[str] = None
    at: datetime
    actor: str


class AlertOut(AlertSummary):
    timeline: list[AlertTimelineItem] = []


class AlertReview(BaseModel):
    note: Optional[str] = Field(default=None, max_length=1000)


class ProfessionalMessage(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class AuthConfig(BaseModel):
    google_client_id: str


class CalendarStatus(BaseModel):
    # Falso = falta `GOOGLE_CLIENT_SECRET` no servidor; o botão fica desligado.
    configured: bool
    connected: bool
    google_email: Optional[str] = None
    connected_at: Optional[datetime] = None
    timezone: str
    # Permissões pedidas na janela do Google (só livre/ocupado).
    requested_scopes: str
    # Conectada, com duração da sessão e horário de atendimento: a SelenIA
    # já consulta a agenda nas conversas.
    ready: bool
    # A conexão tem a permissão de criar eventos.
    events_permission: bool
    # Pronta e com permissão de criar eventos: a SelenIA reserva horários.
    can_book: bool


class CalendarConnect(BaseModel):
    # Código de uso único que a janela de permissão do Google devolve.
    code: str = Field(min_length=1, max_length=2048)


class FreeSlot(BaseModel):
    starts_at: datetime
    label: str


class AppointmentOut(BaseModel):
    id: str
    # tentative, confirmed, rejected, expired ou cancelled.
    status: str
    starts_at: datetime
    ends_at: datetime
    label: str
    patient_name: Optional[str] = None
    # "maria" (pedido na conversa) ou "panel" (marcado pela profissional).
    source: str
    # whatsapp, simulator, ou nulo quando marcado pelo painel.
    channel: Optional[str] = None
    # Mascarado, como nas listas.
    contact_phone: Optional[str] = None
    conversation_id: Optional[str] = None
    created_at: datetime
    expires_at: Optional[datetime] = None
    decided_at: Optional[datetime] = None
    contact_notified: Optional[bool] = None
    # "new" (horário novo), "reschedule" (troca de uma sessão) ou "cancel"
    # (a pessoa pediu para cancelar esta sessão confirmada).
    kind: str = "new"
    # Na troca: a sessão que sai quando a profissional confirmar.
    replaces_label: Optional[str] = None
    # Espera decisão da profissional: pedido provisório ou cancelamento pedido.
    awaiting_decision: bool = False


class GoogleLogin(BaseModel):
    # Token assinado que o botão do Google devolve ao navegador.
    credential: str = Field(min_length=1, max_length=4096)


class MeOut(BaseModel):
    """Quem está logado e, se já concluiu o cadastro, a profissional dele."""

    email: str
    name: Optional[str] = None
    picture_url: Optional[str] = None
    professional: Optional[ProfessionalOut] = None


class CalendarEvent(BaseModel):
    """Um evento da semana no calendário do painel. O título só vai para
    a tela da profissional; não é gravado nem passa pela SelenIA."""

    id: str
    title: str
    starts_at: datetime
    ends_at: datetime
    all_day: bool = False
    # "maria_tentative", "maria_confirmed" (sessões da SelenIA ou do painel)
    # ou "google" (qualquer outro evento da agenda).
    kind: str
    appointment_id: Optional[str] = None


class CalendarEventCreate(BaseModel):
    # "session": sessão com uma pessoa (conta no limite por dia);
    # "block": outro compromisso ou horário bloqueado.
    kind: Literal["session", "block"]
    title: str = Field(min_length=1, max_length=120)
    # Data e hora locais (fuso da agenda), ex.: 2026-09-29T10:00.
    starts_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$")
    minutes: int = Field(ge=5, le=720)


class ClientOut(BaseModel):
    """Uma pessoa que conversou com a SelenIA, na tela Clientes."""

    id: str
    channel: str
    contact_name: str
    # Mascarado, como nas listas.
    contact_phone: Optional[str] = None
    # Nulo = não é cliente ativo.
    active_since: Optional[datetime] = None
    allow_special_hours: bool = False
    special_days: list[str] = []
    # Conversa mais recente, para abrir pelo painel.
    conversation_id: Optional[str] = None
    last_message_at: Optional[datetime] = None
    # Próxima sessão confirmada, já formatada ("terça, 20/10 às 21:00").
    next_session: Optional[str] = None


class ClientUpdate(BaseModel):
    # Tirar da lista (falso) também desliga a permissão e apaga os dias.
    active: Optional[bool] = None
    # Ligar a permissão torna a pessoa cliente ativo.
    allow_special_hours: Optional[bool] = None
    # Dias especiais desta pessoa (só valem com a permissão ligada).
    special_days: Optional[list[Weekday]] = Field(default=None, max_length=7)

    @field_validator("special_days")
    @classmethod
    def week_order(cls, value):
        if value is None:
            return value
        # Na ordem da semana, sem repetir.
        return [day for day in ("mon", "tue", "wed", "thu", "fri", "sat", "sun") if day in value]
