from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401 - registers models with Base before create_all
from app.config import settings
from app.database import Base, engine
from app.routers import chat, documents, professionals

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Chatbot Humanizado TCC")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(professionals.router)
app.include_router(documents.router)
app.include_router(chat.router)


@app.get("/health")
def health():
    return {"status": "ok"}
