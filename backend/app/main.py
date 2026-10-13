import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import SessionLocal
from app.services import appointments, notifications
from app.routers import alerts, assistant, auth, calendar, chat, conversations, documents, professionals, webhook

# A estrutura do banco é criada e evoluída pelo Alembic
# (`alembic upgrade head`), não pela aplicação ao subir. Ter as duas
# coisas criando tabelas levaria o banco e as migrações a divergirem.
# Ver Documentation/tecnico/desenvolvimento.md.

logger = logging.getLogger(__name__)

# De quanto em quanto tempo os pedidos de horário vencidos (24h sem
# decisão) são liberados da agenda.
EXPIRY_CHECK_SECONDS = 300


def _expire_appointments() -> None:
    db = SessionLocal()
    try:
        expired = appointments.expire_overdue(db)
    finally:
        db.close()
    for appointment_id in expired:
        notifications.notify_appointment_expired(appointment_id)


async def _expiry_loop() -> None:
    while True:
        try:
            await run_in_threadpool(_expire_appointments)
        except Exception:
            logger.exception("falha ao liberar pedidos de horário vencidos")
        await asyncio.sleep(EXPIRY_CHECK_SECONDS)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    task = asyncio.create_task(_expiry_loop())
    yield
    task.cancel()


app = FastAPI(title="SelenIA — Assistente para profissionais de saúde mental", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(professionals.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(assistant.router)
app.include_router(conversations.router)
app.include_router(alerts.router)
app.include_router(calendar.router)
app.include_router(webhook.router)


@app.middleware("http")
async def only_webhook_through_tunnel(request: Request, call_next):
    """Pelo endereço público do túnel, só passa o webhook.

    O túnel expõe o backend inteiro na internet. As rotas do painel
    continuam na máquina (o painel fala com a API pelo proxy local), e
    quem chega pelo endereço público só alcança `/webhook/`.
    """
    public = settings.public_webhook_host.strip().lower()
    if public and not request.url.path.startswith("/webhook/"):
        hosts = (request.headers.get("host", ""), request.headers.get("x-forwarded-host", ""))
        if any(h.split(":")[0].strip().lower() == public for h in hosts if h):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
    return await call_next(request)


@app.get("/health")
def health():
    return {"status": "ok"}
