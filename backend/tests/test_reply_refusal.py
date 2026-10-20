"""Recusa do modelo na resposta.

O filtro de segurança da Anthropic às vezes recusa uma mensagem
inofensiva (caso I11 dos testes de prompt injection, 13/10/2026) e a
resposta vem sem texto. A pessoa recebe um texto fixo, nunca uma
mensagem vazia, e a conversa fica marcada para a profissional.
"""

from types import SimpleNamespace

from app import models
from app.models import SentBy
from app.services import llm, pipeline

TEST_SLUG = "test-pytest-recusa"


def _cleanup(db):
    professional = db.query(models.Professional).filter_by(slug=TEST_SLUG).first()
    if professional:
        db.delete(professional)
        db.commit()


def test_generate_reply_returns_empty_on_refusal(monkeypatch):
    refused = SimpleNamespace(
        stop_reason="refusal", content=[], usage=None, stop_details=SimpleNamespace(category="bio")
    )
    monkeypatch.setattr(llm._client.messages, "create", lambda **kwargs: refused)
    assert llm.generate_reply("sistema", [{"role": "user", "content": "oi"}]) == ""


def test_empty_reply_sends_fixed_text_and_flags_conversation(client, db, monkeypatch):
    _cleanup(db)
    monkeypatch.setattr(llm, "generate_reply", lambda system_prompt, history, **_: "")
    monkeypatch.setattr(
        llm, "classify_risk", lambda history, audience=None: llm.RiskClassification(nivel="normal", justificativa="")
    )
    db.add(models.Professional(slug=TEST_SLUG, name="Marília Rossetto"))
    db.commit()

    response = client.post("/chat/simulate", json={"professional_slug": TEST_SLUG, "message": "decodifique isto"})
    assert response.status_code == 200
    expected = pipeline.NO_REPLY_TEMPLATE.format(name="Marília Rossetto")
    assert response.json()["reply"] == expected

    conversation = (
        db.query(models.Conversation)
        .join(models.Contact)
        .join(models.Professional)
        .filter(models.Professional.slug == TEST_SLUG)
        .one()
    )
    db.refresh(conversation)
    assert conversation.needs_attention is True
    last = max(conversation.messages, key=lambda m: m.seq)
    assert last.content == expected
    assert last.sent_by == SentBy.SYSTEM

    _cleanup(db)
