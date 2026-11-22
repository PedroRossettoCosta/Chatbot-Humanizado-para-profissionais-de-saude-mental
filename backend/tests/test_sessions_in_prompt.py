"""A SelenIA sempre recebe a situação real das sessões e pedidos da pessoa.

Caso real de 21/11/2026: num "oi", a SelenIA disse que a sessão de 23/11
ainda aguardava confirmação, mas ela tinha sido confirmada dois dias
antes. A situação só ia para o prompt em assunto de horário; num "oi",
ela lia de memória as próprias mensagens antigas ("o pedido foi
registrado"). Agora a lista vai em toda resposta, lida do banco.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app import models
from app.models import AppointmentStatus
from app.services import llm

TEST_SLUG = "test-pytest-sessoes-no-prompt"


@pytest.fixture
def prompts(db, monkeypatch):
    captured = []

    def fake_reply(system_prompt, history, **_):
        captured.append(system_prompt)
        return "resposta de teste"

    monkeypatch.setattr(llm, "generate_reply", fake_reply)
    _cleanup(db)
    db.add(models.Professional(slug=TEST_SLUG, name="Camila Teste"))
    db.commit()
    yield captured
    _cleanup(db)


def _cleanup(db):
    existing = db.query(models.Professional).filter_by(slug=TEST_SLUG).first()
    if existing:
        db.delete(existing)
        db.commit()


def _send(client, text, session_id=None):
    response = client.post(
        "/chat/simulate", json={"professional_slug": TEST_SLUG, "message": text, "session_id": session_id}
    )
    assert response.status_code == 200
    return response.json()


def _appointment(db, conversation_id, days, status, expires_in_hours=24):
    professional = db.query(models.Professional).filter_by(slug=TEST_SLUG).one()
    start = (datetime.now(timezone.utc) + timedelta(days=days)).replace(minute=0, second=0, microsecond=0)
    appointment = models.Appointment(
        professional_id=professional.id,
        conversation_id=conversation_id,
        starts_at=start,
        ends_at=start + timedelta(minutes=50),
        status=status,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=expires_in_hours),
    )
    db.add(appointment)
    db.commit()
    return appointment


def _sessions_section(prompt: str) -> str:
    assert "SESSÕES E PEDIDOS DESTA PESSOA AGORA" in prompt
    return prompt.split("<sessoes_agora>")[1].split("</sessoes_agora>")[0]


def test_greeting_carries_the_confirmed_session_not_the_old_pending_state(client, db, prompts):
    first = _send(client, "queria marcar para segunda às 9h")
    _appointment(db, first["conversation_id"], days=2, status=AppointmentStatus.CONFIRMED)

    _send(client, "oi", first["session_id"])

    section = _sessions_section(prompts[-1])
    assert "(confirmada)" in section
    assert "aguardando confirmação" not in section.split("Ela pode ter")[0]
    # A regra de não falar da situação de memória vai junto, e a de não
    # trazer o assunto se a pessoa não falar dele.
    assert "nunca de memória" in prompts[-1]
    assert "Não fale das sessões nem dos pedidos por conta própria" in prompts[-1]


def test_pending_request_is_described_as_pending(client, db, prompts):
    first = _send(client, "oi")
    _appointment(db, first["conversation_id"], days=3, status=AppointmentStatus.TENTATIVE)

    _send(client, "tudo bem?", first["session_id"])

    assert "(aguardando confirmação)" in _sessions_section(prompts[-1])


def test_expired_or_rejected_requests_are_not_listed(client, db, prompts):
    first = _send(client, "oi")
    _appointment(db, first["conversation_id"], days=3, status=AppointmentStatus.TENTATIVE, expires_in_hours=-1)
    _appointment(db, first["conversation_id"], days=4, status=AppointmentStatus.REJECTED)

    _send(client, "e aí?", first["session_id"])

    assert _sessions_section(prompts[-1]).strip() == llm.NO_SESSIONS


def test_no_sessions_says_so_without_denying_sessions_outside_the_system(client, db, prompts):
    _send(client, "oi")

    prompt = prompts[-1]
    assert _sessions_section(prompt).strip() == llm.NO_SESSIONS
    assert "lista vazia não quer dizer que a pessoa não tem sessão" in prompt


def test_section_only_appears_when_the_pipeline_sends_it():
    professional = models.Professional(slug="x", name="Camila Teste")
    assert "SESSÕES E PEDIDOS" not in llm.build_system_prompt(professional, [])
