from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import alerts, assistant, auth, chat, conversations, documents, professionals

# A estrutura do banco é criada e evoluída pelo Alembic
# (`alembic upgrade head`), não pela aplicação ao subir. Ter as duas
# coisas criando tabelas levaria o banco e as migrações a divergirem.
# Ver Documentation/tecnico/desenvolvimento.md.

app = FastAPI(title="MarIA — Assistente para profissionais de saúde mental")

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


@app.get("/health")
def health():
    return {"status": "ok"}
