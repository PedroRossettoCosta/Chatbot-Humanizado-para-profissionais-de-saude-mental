from fastapi import FastAPI

from app import models  # noqa: F401 - registers models with Base before create_all
from app.database import Base, engine
from app.routers import chat, documents, professionals

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Chatbot Humanizado TCC")

app.include_router(professionals.router)
app.include_router(documents.router)
app.include_router(chat.router)


@app.get("/health")
def health():
    return {"status": "ok"}
