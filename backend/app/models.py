"""Modelo de dados do SelenIA.

Visão geral das tabelas e de como elas se ligam:

    User ── UserSession  (quem entra no painel com o Google, e suas sessões)
      │
    Professional  (a profissional dona da conta)
      ├── Document       (arquivos da base de conhecimento / RAG)
      ├── Contact        (quem fala com o bot: um lead ou paciente)
      │     └── Conversation   (uma thread de atendimento)
      │           ├── Message        (cada mensagem trocada)
      │           ├── SafetyAlert    (disparos da triagem de segurança)
      │           │     └── SafetyAlertEvent   (trilha de auditoria)
      │           └── Appointment    (pré-agendamento no Google Calendar)
      └── LlmUsage       (tokens de cada chamada ao modelo, sem conteúdo)

Três decisões que valem explicação:

1. **Um canal é uma coluna, não uma tabela.** WhatsApp, simulador e
   (no futuro) Instagram compartilham as mesmas tabelas, distinguidos
   pelo campo `channel`. Assim a triagem, o RAG e o painel funcionam
   igual para todos, e um canal novo não obriga a duplicar nada.

2. **Dados pessoais vão cifrados** (`EncryptedText`). Para conseguir
   *procurar* por um telefone cifrado, o `Contact` guarda também um
   índice cego (ver `services/crypto.py`).

3. **Alertas de segurança não são editáveis.** O `SafetyAlert` nunca
   muda depois de criado; "visualizado" e "revisado" viram linhas novas
   em `SafetyAlertEvent`. Isso atende ao requisito de auditabilidade
   (RNF05 em `levantamento-requisitos-mvp.md`).
"""

import uuid
from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator

from app.database import Base
from app.services import crypto


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    """Horário atual em UTC, com fuso explícito.

    O banco guarda sempre em UTC; a conversão para o horário de Brasília
    acontece na exibição. Isso evita ambiguidade no horário de verão e
    em agendamentos.
    """
    return datetime.now(timezone.utc)


class EncryptedText(TypeDecorator):
    """Texto cifrado em repouso (LGPD) — transparente para o resto do código.

    Quem lê `message.content` recebe o texto normal; quem olha a coluna
    direto no Postgres vê só a cifra.
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return crypto.encrypt(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return crypto.decrypt(value)


# ---------------------------------------------------------------------------
# Valores fixos (guardados como texto, validados no código)
# ---------------------------------------------------------------------------


class Channel(StrEnum):
    """Por onde a conversa acontece."""

    SIMULATOR = "simulator"  # chat de teste do painel
    WHATSAPP = "whatsapp"


class ConversationState(StrEnum):
    """Quem está conduzindo a conversa neste momento."""

    ACTIVE = "active"  # o bot responde normalmente
    HUMAN = "human"  # a profissional assumiu; o bot fica em silêncio
    EMERGENCY_HOLD = "emergency_hold"  # protocolo de emergência disparado


class ContactType(StrEnum):
    """Usado pela política de retenção, que é diferente para cada um."""

    LEAD = "lead"  # procurou, ainda não virou paciente
    PATIENT = "patient"  # já iniciou atendimento


class AwaitingReason(StrEnum):
    """Por que a conversa ficou "Aguardando você"."""

    WANTS_PROFESSIONAL = "falar_com_profissional"  # pediu para falar com ela
    REFUSES_BOT = "recusa_bot"  # não quer falar com o bot
    # Pedidos que a SelenIA leva pela ferramenta `avisar_profissional`:
    SPECIAL_HOURS = "horario_especial"  # horário fora do atendimento
    PAYMENT = "pagamento"  # forma de pagamento que a SelenIA não sabe
    PRICE = "valor"  # desconto, outro valor, valor não informado
    OTHER = "outro"  # outra dúvida que só ela responde


class MessageRole(StrEnum):
    """Papel da mensagem na conversa (o mesmo vocabulário da API da Claude)."""

    USER = "user"  # veio do contato
    ASSISTANT = "assistant"  # saiu do sistema


class SentBy(StrEnum):
    """Quem escreveu uma mensagem de saída."""

    BOT = "bot"
    PROFESSIONAL = "professional"  # a profissional respondeu pelo painel
    SYSTEM = "system"  # texto fixo (aviso de IA, mensagem de emergência)


class AlertLevel(StrEnum):
    """Níveis definidos pela profissional no protocolo e na rotulagem de 23/09."""

    EMERGENCY = "emergency"  # risco à vida: interrompe o fluxo e encaminha
    # Referência a morte com intenção incerta ("quero morrer" pode ser
    # expressão forte): avisa a profissional e o bot segue a conversa.
    POSSIBLE_RISK = "possible_risk"
    INTENSE_SUFFERING = "intense_suffering"  # sinaliza para atenção humana
    # Não é risco: a pessoa recusou falar com o bot. Usa a mesma tabela
    # para chegar à profissional pelo mesmo caminho (tela e aviso), mas
    # fica fora das métricas da triagem, que filtram pelos níveis acima.
    BOT_REFUSED = "bot_refused"


class AlertEventType(StrEnum):
    VIEWED = "viewed"
    REVIEWED = "reviewed"
    NOTIFIED = "notified"  # aviso enviado à profissional (WhatsApp/e-mail)
    # A profissional liberou o bot para voltar a responder na conversa.
    BOT_RELEASED = "bot_released"
    # O aviso por e-mail não saiu (sem endereço, sem SMTP ou erro no
    # envio). Fica na trilha para que um alerta que não chegou à
    # profissional não passe despercebido.
    NOTIFY_FAILED = "notify_failed"


class AppointmentStatus(StrEnum):
    TENTATIVE = "tentative"  # criado pelo bot, aguardando aprovação
    CONFIRMED = "confirmed"  # a profissional aprovou
    REJECTED = "rejected"  # a profissional recusou
    EXPIRED = "expired"  # ninguém decidiu a tempo; o horário foi liberado
    CANCELLED = "cancelled"  # a mesma pessoa pediu outro horário


# Pedidos que ocupam o horário. Dois deles nunca podem ter o mesmo início
# para a mesma profissional (índice `uq_appointment_active_slot`).
ACTIVE_APPOINTMENT_STATUSES = (AppointmentStatus.TENTATIVE, AppointmentStatus.CONFIRMED)


# ---------------------------------------------------------------------------
# Tabelas
# ---------------------------------------------------------------------------


class Professional(Base):
    """A profissional de saúde mental dona da conta (um tenant)."""

    __tablename__ = "professionals"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    slug = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    voice_tone = Column(Text, nullable=True)
    # Especialidade e público, escritos pela profissional. A triagem usa
    # isto só para entender o que é sofrimento comum naquele consultório
    # (normal x sofrimento intenso); nunca rebaixa dúvida ou emergência.
    audience_description = Column(Text, nullable=True)
    # Como funciona o atendimento e quanto custa, nas palavras dela. Fica
    # sempre no prompt (e não só nos documentos do RAG) porque o preço é
    # respondido logo na primeira pergunta e não pode depender da busca.
    service_info = Column(Text, nullable=True)
    # Respostas às perguntas fixas de `services/guidelines.VOICE_QUESTIONS`,
    # no formato {chave: {"good": "...", "bad": "..."}}.
    voice_examples = Column(JSON, nullable=True)
    # Itens de "nunca dizer" acrescentados por ela, além dos fixos do
    # produto (`guidelines.NEVER_SAY_DEFAULTS`). Lista de textos.
    extra_never_say = Column(JSON, nullable=True)
    # Agenda do Google usada para pré-agendamento. Fica por profissional
    # para que cada uma exponha só a agenda que quiser.
    calendar_id = Column(String(255), nullable=True)
    # Onde ela recebe os alertas por e-mail. Quem envia é a conta do
    # produto (`settings.smtp_*`), igual para todas.
    alert_email = Column(String(255), nullable=True)
    # Botão "Em consulta" do painel. Nulo = desligado. Com `in_session_since`
    # preenchido e `in_session_until` nulo, fica ligado até ela desligar;
    # com os dois, desliga sozinho no horário (para não ficar esquecido
    # ligado o dia inteiro). Ver `is_in_session`.
    in_session_since = Column(DateTime(timezone=True), nullable=True)
    in_session_until = Column(DateTime(timezone=True), nullable=True)
    # Duração de uma sessão, em minutos. A agenda usa para montar os
    # horários oferecidos; o texto livre de `service_info` não serve
    # para isso.
    session_minutes = Column(Integer, nullable=True)
    # Dias e horários em que ela atende, no fuso `settings.agenda_timezone`.
    # A SelenIA só oferece horário livre dentro disto. Formato:
    # {"mon": [{"start": "10:00", "end": "16:00"}], ...}; dia ausente ou
    # lista vazia = não atende (ver `services/calendar.WEEKDAYS`).
    working_hours = Column(JSON, nullable=True)
    # Quantas sessões por dia a SelenIA pode deixar marcadas (pedidos
    # aguardando + confirmados + as marcadas pelo painel). Nulo = sem limite.
    max_sessions_per_day = Column(Integer, nullable=True)
    # Formas de pagamento que ela aceita: lista de chaves de
    # `guidelines.PAYMENT_METHODS` (ex.: ["pix", "credito"]). Nulo ou
    # vazio = não informado, e a SelenIA pergunta a ela.
    payment_methods = Column(JSON, nullable=True)
    # Cadastro em etapas: onde ela parou (1 a 7), quando aceitou as
    # regras fixas da SelenIA e quando concluiu. O painel só libera com o
    # cadastro concluído.
    onboarding_step = Column(Integer, nullable=True)
    rules_accepted_at = Column(DateTime(timezone=True), nullable=True)
    onboarding_completed_at = Column(DateTime(timezone=True), nullable=True)
    # Como a SelenIA fala dela com o paciente: "feminine", "masculine" ou
    # "neutral" (ver `guidelines.PRONOUNS`). Nulo = neutro.
    pronouns = Column(String(20), nullable=True)
    # Número da SelenIA desta profissional no WhatsApp (o "phone number ID"
    # da Meta). O webhook diz para qual número a pessoa escreveu, e é
    # assim que a mensagem chega à profissional certa.
    whatsapp_phone_number_id = Column(String(32), nullable=True, unique=True)
    # Conexão do número pelo painel (`services/whatsapp_numbers.py`). O
    # número fica "pendente" (já na conta da Meta, ainda sem receber
    # mensagens) até o registro; só então vira `whatsapp_phone_number_id`.
    whatsapp_pending_id = Column(String(32), nullable=True)
    whatsapp_setup_step = Column(String(20), nullable=True)  # code_sent, verified
    whatsapp_display_number = Column(String(32), nullable=True)
    whatsapp_verified_name = Column(String(255), nullable=True)
    # PIN da verificação em duas etapas do número, cifrado (`crypto`).
    whatsapp_pin = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)

    @property
    def is_in_session(self) -> bool:
        if self.in_session_since is None:
            return False
        return self.in_session_until is None or self.in_session_until > _now()

    documents = relationship("Document", back_populates="professional", cascade="all, delete-orphan")
    contacts = relationship("Contact", back_populates="professional", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="professional", cascade="all, delete-orphan")
    calendar_connection = relationship(
        "CalendarConnection", back_populates="professional", uselist=False, cascade="all, delete-orphan"
    )
    appointments = relationship("Appointment", back_populates="professional", cascade="all, delete-orphan")


class WhatsAppRegisterAttempt(Base):
    """Cada chamada de registro de número na Meta.

    A Meta aceita 10 registros por número em 72 horas; o 11º bloqueia o
    número por mais 72 horas. Contar aqui deixa o painel parar antes.
    """

    __tablename__ = "whatsapp_register_attempts"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    professional_id = Column(
        UUID(as_uuid=False), ForeignKey("professionals.id", ondelete="CASCADE"), nullable=False
    )
    phone_number_id = Column(String(32), nullable=False, index=True)
    ok = Column(Boolean, nullable=False)
    error_code = Column(String(32), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)


class CalendarConnection(Base):
    """Acesso ao Google Agenda que a profissional deu pelo painel.

    Só a disponibilidade (livre/ocupado) da agenda principal: com esse
    acesso, a SelenIA não vê título, descrição nem convidados dos eventos,
    que podem ter nome de paciente. Ver `services/calendar.py`.
    """

    __tablename__ = "calendar_connections"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    professional_id = Column(UUID(as_uuid=False), ForeignKey("professionals.id"), nullable=False, unique=True)
    # Conta Google da agenda. Pode ser diferente da que entra no painel.
    google_email = Column(String(255), nullable=False)
    # Código de longa duração que o Google devolve na permissão. Dá acesso
    # à agenda sem ela estar no painel, por isso vai cifrado.
    refresh_token = Column(EncryptedText, nullable=False)
    scopes = Column(Text, nullable=False)
    connected_at = Column(DateTime(timezone=True), default=_now)

    professional = relationship("Professional", back_populates="calendar_connection")


class Document(Base):
    """Arquivo da base de conhecimento. O texto vive no ChromaDB; aqui fica o registro."""

    __tablename__ = "documents"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    professional_id = Column(UUID(as_uuid=False), ForeignKey("professionals.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=True)
    chunk_count = Column(Integer, default=0)
    uploaded_at = Column(DateTime(timezone=True), default=_now)

    professional = relationship("Professional", back_populates="documents")


class Contact(Base):
    """Quem conversa com o bot, do outro lado do canal.

    `external_id` é o identificador no canal de origem: o número no
    WhatsApp, ou o id de sessão no simulador. Ele vai cifrado, e a busca
    acontece pelo `external_id_index` (ver `services/crypto.py`).
    """

    __tablename__ = "contacts"
    __table_args__ = (
        # O mesmo identificador, no mesmo canal, é sempre o mesmo contato
        # — mas só dentro da conta daquela profissional.
        UniqueConstraint("professional_id", "channel", "external_id_index", name="uq_contact_por_canal"),
    )

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    professional_id = Column(UUID(as_uuid=False), ForeignKey("professionals.id"), nullable=False, index=True)
    channel = Column(String(20), nullable=False)
    external_id = Column(EncryptedText, nullable=False)
    external_id_index = Column(String(64), nullable=False, index=True)
    # Nome que o próprio canal informa (no WhatsApp, o nome do perfil).
    display_name = Column(EncryptedText, nullable=True)
    # Cliente ativo (tela Clientes): desde quando. Vira ativo sozinho
    # quando a profissional confirma uma sessão pedida na conversa, ou
    # quando ela marca no painel. Nulo = não é cliente ativo.
    active_since = Column(DateTime(timezone=True), nullable=True)
    # Permissão dada pela profissional para esta pessoa ter condição
    # especial: o limite de sessões por dia não vale para ela, e nos seus
    # dias especiais (`special_days`) ela marca em qualquer horário livre.
    # Só vale com o cliente ativo; tirar o cliente da lista desliga a
    # permissão e apaga os dias.
    allow_special_hours = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    # Dias especiais desta pessoa: dias da semana (ex.: ["tue", "sat"]),
    # escolhidos pela profissional na tela Clientes.
    special_days = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)

    @property
    def can_use_special_hours(self) -> bool:
        return self.active_since is not None and bool(self.allow_special_hours)

    professional = relationship("Professional", back_populates="contacts")
    conversations = relationship("Conversation", back_populates="contact", cascade="all, delete-orphan")


class Conversation(Base):
    """Uma thread de atendimento entre um contato e a profissional."""

    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    professional_id = Column(UUID(as_uuid=False), ForeignKey("professionals.id"), nullable=False, index=True)
    contact_id = Column(UUID(as_uuid=False), ForeignKey("contacts.id"), nullable=False, index=True)
    state = Column(String(20), nullable=False, default=ConversationState.ACTIVE)
    # Marcação "necessita atenção da Marília": sofrimento intenso que não
    # é emergência. Fica separado do estado porque o bot continua
    # atendendo normalmente enquanto isso.
    needs_attention = Column(Boolean, nullable=False, default=False)
    # "Aguardando você": a pessoa pediu para falar com a profissional (ou
    # recusou o bot) e ainda não recebeu resposta dela. Separado de
    # `needs_attention`, que é sinal da triagem, não pedido da pessoa.
    # Sai quando ela responde ou devolve a conversa ao bot.
    awaiting_reply_since = Column(DateTime(timezone=True), nullable=True)
    # Por que a conversa está aguardando (`AwaitingReason`): o painel e o
    # e-mail dizem o tipo do pedido, nunca o texto da conversa.
    awaiting_reason = Column(String(30), nullable=True)
    # Última mensagem **do contato**. Conta a janela de 24h do WhatsApp:
    # fora dela, só modelo aprovado pela Meta, que o MVP não usa.
    last_contact_message_at = Column(DateTime(timezone=True), nullable=True)
    contact_type = Column(String(20), nullable=False, default=ContactType.LEAD)
    created_at = Column(DateTime(timezone=True), default=_now)
    last_message_at = Column(DateTime(timezone=True), default=_now)

    professional = relationship("Professional", back_populates="conversations")
    contact = relationship("Contact", back_populates="conversations")
    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.seq"
    )
    alerts = relationship("SafetyAlert", back_populates="conversation", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    """Uma mensagem trocada. O conteúdo é sempre cifrado em repouso."""

    __tablename__ = "messages"
    __table_args__ = (
        # A Meta reenvia o mesmo webhook quando não recebe confirmação;
        # esta restrição impede processar a mensagem duas vezes.
        UniqueConstraint("external_id", name="uq_message_external_id"),
        Index("ix_message_conversa_seq", "conversation_id", "seq"),
    )

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    # Ordem de inserção, garantida pelo banco. O horário não serve como
    # critério de ordenação: o relógio do sistema tem resolução de
    # milissegundos, então duas mensagens seguidas podem receber o mesmo
    # `created_at` e a ordem do histórico ficaria indefinida.
    seq = Column(BigInteger, Identity(), nullable=False, unique=True)
    conversation_id = Column(UUID(as_uuid=False), ForeignKey("conversations.id"), nullable=False)
    role = Column(String(16), nullable=False)
    content = Column(EncryptedText, nullable=False)
    # Só nas mensagens de saída: diferencia o que o bot escreveu do que a
    # profissional escreveu pelo painel.
    sent_by = Column(String(20), nullable=True)
    # Identificador da mensagem no canal de origem (no WhatsApp, o `wamid`).
    external_id = Column(String(128), nullable=True)
    # Só no WhatsApp: a Meta recusou o envio desta mensagem de saída (ex.:
    # erro 131042, falta de forma de pagamento). O painel mostra "não
    # entregue".
    delivery_failed = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    # Foto, áudio ou documento recebido pelo WhatsApp: só a referência da
    # Meta, nunca o arquivo. O painel busca na Meta quando a profissional
    # abre (`whatsapp.fetch_media`); a Meta guarda por cerca de 30 dias.
    media_type = Column(String(16), nullable=True)  # image, audio, document
    media_id = Column(String(64), nullable=True)
    media_mime = Column(String(100), nullable=True)
    # Nome do arquivo do documento: pode dizer muito ("exame.pdf"), cifrado.
    media_filename = Column(EncryptedText, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)

    conversation = relationship("Conversation", back_populates="messages")


class SafetyAlert(Base):
    """Disparo da triagem de segurança. Imutável depois de criado.

    Mudanças de situação (visualizado, revisado) viram linhas em
    `SafetyAlertEvent`, para que exista uma trilha de auditoria e a
    profissional não consiga apagar um alerta.
    """

    __tablename__ = "safety_alerts"
    __table_args__ = (Index("ix_alerta_profissional_data", "professional_id", "created_at"),)

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    professional_id = Column(UUID(as_uuid=False), ForeignKey("professionals.id"), nullable=False)
    conversation_id = Column(UUID(as_uuid=False), ForeignKey("conversations.id"), nullable=False, index=True)
    # Mensagem que disparou o alerta. Fica nulo se a mensagem for apagada
    # pela política de retenção — o alerta em si permanece.
    message_id = Column(UUID(as_uuid=False), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    level = Column(String(30), nullable=False)
    # Qual camada e regra da triagem disparou (ex.: "camada1:suicidio").
    # Sem conteúdo da mensagem, então não precisa de cifra e sobrevive à
    # retenção: é o que permite medir falsos positivos depois.
    trigger = Column(String(64), nullable=True)
    # Trecho que motivou o disparo, para a profissional entender o porquê
    # sem precisar abrir a conversa inteira.
    excerpt = Column(EncryptedText, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)

    conversation = relationship("Conversation", back_populates="alerts")
    events = relationship(
        "SafetyAlertEvent",
        back_populates="alert",
        cascade="all, delete-orphan",
        order_by="SafetyAlertEvent.created_at",
    )


class SafetyAlertEvent(Base):
    """Trilha de auditoria de um alerta: só acrescenta, nunca altera."""

    __tablename__ = "safety_alert_events"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    alert_id = Column(UUID(as_uuid=False), ForeignKey("safety_alerts.id"), nullable=False, index=True)
    event_type = Column(String(20), nullable=False)
    # Quem provocou o evento: "system" ou o id da profissional.
    actor = Column(String(64), nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)

    alert = relationship("SafetyAlert", back_populates="events")


class Appointment(Base):
    """Pré-agendamento criado pelo bot, espelhado no Google Calendar.

    Nasce provisório (`tentative`), com evento "(a confirmar)" na agenda,
    e a profissional confirma ou recusa no painel. Sem decisão até
    `expires_at`, expira e o evento sai da agenda.
    """

    __tablename__ = "appointments"
    __table_args__ = (
        # Rede de segurança contra duas pessoas no mesmo horário: a regra
        # principal é a trava em `services/appointments.request`.
        Index(
            "uq_appointment_active_slot",
            "professional_id",
            "starts_at",
            unique=True,
            postgresql_where=text("status IN ('tentative', 'confirmed')"),
        ),
    )

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    professional_id = Column(UUID(as_uuid=False), ForeignKey("professionals.id"), nullable=False, index=True)
    # Nulo quando a própria profissional marcou pelo painel.
    conversation_id = Column(UUID(as_uuid=False), ForeignKey("conversations.id"), nullable=True)
    # "maria" (pedido feito na conversa) ou "panel" (marcado pela profissional).
    source = Column(String(20), nullable=False, default="maria", server_default="maria")
    # Guardados aqui para que o evento continue rastreável mesmo se a
    # profissional trocar de agenda depois.
    calendar_id = Column(String(255), nullable=True)
    calendar_event_id = Column(String(255), nullable=True)
    starts_at = Column(DateTime(timezone=True), nullable=False)
    ends_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(20), nullable=False, default=AppointmentStatus.TENTATIVE)
    # Nome que a pessoa deu na conversa (vai também no evento da agenda).
    patient_name = Column(EncryptedText, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    # Se a mensagem de confirmação ou recusa chegou à pessoa. Falso quando
    # a janela de 24h do WhatsApp já fechou ou o envio falhou.
    contact_notified = Column(Boolean, nullable=True)
    # Remarcar e cancelar como pedido (Pedro, 12/10/2026). No pedido de
    # troca, a sessão que ele substitui quando a profissional confirmar.
    replaces_id = Column(UUID(as_uuid=False), ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True)
    # A pessoa pediu para cancelar esta sessão confirmada e a profissional
    # ainda não decidiu. Até lá a sessão continua de pé.
    cancel_requested_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)

    conversation = relationship("Conversation", back_populates="appointments")
    professional = relationship("Professional", back_populates="appointments")
    replaces = relationship("Appointment", remote_side=[id])


# ---------------------------------------------------------------------------
# Acesso ao painel
# ---------------------------------------------------------------------------


class User(Base):
    """Quem entra no painel, identificado pela conta Google.

    Separado de `Professional` porque são coisas diferentes: a conta é
    quem faz login; a profissional é o consultório que a SelenIA atende.
    No MVP é uma para uma, e `professional_id` fica nulo até o cadastro
    ser concluído. Não há senha: quem prova a identidade é o Google.
    """

    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    # Identificador permanente da conta no Google (`sub` do token). O
    # e-mail pode mudar; o `sub`, não.
    google_sub = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)
    picture_url = Column(String(1024), nullable=True)
    professional_id = Column(
        UUID(as_uuid=False),
        ForeignKey("professionals.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
    created_at = Column(DateTime(timezone=True), default=_now)
    last_login_at = Column(DateTime(timezone=True), default=_now)

    professional = relationship("Professional")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")

    def owns(self, professional_id: str) -> bool:
        return self.professional_id is not None and self.professional_id == professional_id


class UserSession(Base):
    """Sessão de login no painel, guardada no banco para poder ser encerrada.

    O navegador recebe um código aleatório num cookie `httpOnly`; aqui
    fica só o hash dele. Quem ler o banco não consegue se passar pela
    profissional.
    """

    __tablename__ = "user_sessions"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    user = relationship("User", back_populates="sessions")


class LlmUsage(Base):
    """Tokens de uma chamada ao modelo, para medir o custo de verdade.

    Uma linha por chamada (cada rodada de ferramenta é uma chamada). Só
    números: nunca o texto enviado ou recebido. A linha continua quando
    a conversa é apagada pela retenção (`conversation_id` vira nulo),
    para o custo do mês não sumir junto.
    """

    __tablename__ = "llm_usage"
    __table_args__ = (Index("ix_uso_profissional_data", "professional_id", "created_at"),)

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    professional_id = Column(
        UUID(as_uuid=False), ForeignKey("professionals.id", ondelete="CASCADE"), nullable=False
    )
    conversation_id = Column(
        UUID(as_uuid=False), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True
    )
    # "reply" (resposta da SelenIA) ou "triage" (camada 2 da triagem).
    purpose = Column(String(20), nullable=False)
    model = Column(String(64), nullable=False)
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    cache_read_tokens = Column(Integer, nullable=False, default=0)
    cache_write_tokens = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=_now)
