"""Uso de tokens: cada chamada ao modelo vira uma linha, sem conteúdo,
e a parte fixa do prompt vai com cache."""

from types import SimpleNamespace

import pytest

from app import models
from app.services import llm

TEST_SLUG = "test-pytest-uso"


def _usage(input_tokens, output_tokens, cache_read=0, cache_write=0):
    return SimpleNamespace(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_input_tokens=cache_read,
        cache_creation_input_tokens=cache_write,
    )


@pytest.fixture
def api(db, monkeypatch):
    """Substitui o cliente da Claude: guarda o que foi enviado e devolve
    uma resposta com uso conhecido."""
    sent = []

    def create(**kwargs):
        sent.append(kwargs)
        return SimpleNamespace(
            stop_reason="end_turn",
            content=[SimpleNamespace(type="text", text="resposta do bot")],
            usage=_usage(1200, 80, cache_read=900),
        )

    monkeypatch.setattr(llm, "_client", SimpleNamespace(messages=SimpleNamespace(create=create)))

    def classify(history, audience=None):
        llm._note_usage("triage", "modelo-da-triagem", _usage(400, 30))
        return llm.RiskClassification(nivel="normal", justificativa="teste")

    monkeypatch.setattr(llm, "classify_risk", classify)
    _cleanup(db)
    db.add(models.Professional(slug=TEST_SLUG, name="Marília Rossetto"))
    db.commit()
    yield sent
    _cleanup(db)


def _cleanup(db):
    existing = db.query(models.Professional).filter_by(slug=TEST_SLUG).first()
    if existing:
        db.delete(existing)
        db.commit()


def test_each_call_is_recorded_without_content(db, client, api):
    body = client.post("/chat/simulate", json={"professional_slug": TEST_SLUG, "message": "quanto custa?"}).json()
    rows = (
        db.query(models.LlmUsage)
        .filter_by(conversation_id=body["conversation_id"])
        .order_by(models.LlmUsage.purpose)
        .all()
    )
    assert [(r.purpose, r.input_tokens, r.output_tokens, r.cache_read_tokens) for r in rows] == [
        ("reply", 1200, 80, 900),
        ("triage", 400, 30, 0),
    ]
    assert rows[0].model == llm.settings.claude_model
    # A tabela só tem números e identificadores, nenhuma coluna de texto livre.
    columns = {c.name for c in models.LlmUsage.__table__.columns}
    assert "content" not in columns and "text" not in columns


def test_fixed_part_of_the_prompt_is_cached(client, api):
    client.post("/chat/simulate", json={"professional_slug": TEST_SLUG, "message": "oi"})
    fixed, context = api[-1]["system"]
    assert fixed["cache_control"] == {"type": "ephemeral"}
    assert "PAPEL E LIMITES" in fixed["text"] and "Marília Rossetto" in fixed["text"]
    assert context["text"].startswith(llm.CONTEXT_HEADER)
    assert "cache_control" not in context


def test_nothing_is_noted_outside_collect_usage():
    llm._note_usage("reply", "modelo", _usage(1, 1))  # não levanta e não guarda
    with llm.collect_usage() as calls:
        llm._note_usage("reply", "modelo", _usage(5, 2))
    assert calls == [
        {
            "purpose": "reply",
            "model": "modelo",
            "input_tokens": 5,
            "output_tokens": 2,
            "cache_read_tokens": 0,
            "cache_write_tokens": 0,
        }
    ]
