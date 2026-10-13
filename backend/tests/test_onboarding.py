"""Cadastro em etapas: progresso, aceite das regras e conclusão."""

from app import models

TEST_SLUG = "test-pytest-cadastro"

COMPLETE_PROFILE = {
    "alert_email": "alertas@teste.local",
    "pronouns": "feminine",
    "audience_description": "Psicanalista; adultos.",
    "service_info": "Online, R$ 200 por sessão.",
    "session_minutes": 50,
    "voice_tone": "acolhedor",
    "voice_examples": {
        key: {"good": "boa", "bad": "ruim"} for key in ("preco", "funcionamento", "momento_dificil")
    },
}


def _cleanup(db):
    db.query(models.Professional).filter_by(slug=TEST_SLUG).delete()
    db.commit()


def test_creating_the_professional_moves_to_step_two(client, db):
    _cleanup(db)
    body = client.post("/professionals", json={"slug": TEST_SLUG, "name": "Teste Cadastro"}).json()
    assert body["onboarding_step"] == 2
    assert body["onboarding_completed_at"] is None
    _cleanup(db)


def test_progress_and_session_length_are_saved(client, db):
    _cleanup(db)
    client.post("/professionals", json={"slug": TEST_SLUG, "name": "Teste Cadastro"})

    response = client.patch(f"/professionals/{TEST_SLUG}", json={"session_minutes": 50, "onboarding_step": 3})
    assert response.status_code == 200
    assert response.json()["session_minutes"] == 50
    assert response.json()["onboarding_step"] == 3

    assert client.patch(f"/professionals/{TEST_SLUG}", json={"session_minutes": 5}).status_code == 422
    assert client.patch(f"/professionals/{TEST_SLUG}", json={"onboarding_step": 8}).status_code == 422
    _cleanup(db)


def test_cannot_complete_with_missing_fields(client, db):
    _cleanup(db)
    client.post("/professionals", json={"slug": TEST_SLUG, "name": "Teste Cadastro"})

    response = client.post(f"/professionals/{TEST_SLUG}/complete-onboarding")
    assert response.status_code == 422
    missing = response.json()["detail"]["missing"]
    assert "Duração da sessão" in missing
    assert "Como a SelenIA fala de você" in missing
    assert "Aceite das regras da SelenIA" in missing
    _cleanup(db)


def test_example_without_bad_answer_is_missing(client, db):
    _cleanup(db)
    client.post("/professionals", json={"slug": TEST_SLUG, "name": "Teste Cadastro"})
    profile = {**COMPLETE_PROFILE, "voice_examples": {**COMPLETE_PROFILE["voice_examples"], "preco": {"good": "x"}}}
    client.patch(f"/professionals/{TEST_SLUG}", json=profile)
    client.post(f"/professionals/{TEST_SLUG}/accept-rules")

    missing = client.post(f"/professionals/{TEST_SLUG}/complete-onboarding").json()["detail"]["missing"]
    assert missing == ['Respostas boa e ruim para "Quanto custa a consulta?"']
    _cleanup(db)


def test_accept_rules_then_complete(client, db):
    _cleanup(db)
    client.post("/professionals", json={"slug": TEST_SLUG, "name": "Teste Cadastro"})
    client.patch(f"/professionals/{TEST_SLUG}", json=COMPLETE_PROFILE)

    accepted = client.post(f"/professionals/{TEST_SLUG}/accept-rules").json()
    assert accepted["rules_accepted_at"] is not None

    response = client.post(f"/professionals/{TEST_SLUG}/complete-onboarding")
    assert response.status_code == 200
    completed_at = response.json()["onboarding_completed_at"]
    assert completed_at is not None

    # Concluir de novo não muda a data original.
    again = client.post(f"/professionals/{TEST_SLUG}/complete-onboarding").json()
    assert again["onboarding_completed_at"] == completed_at
    _cleanup(db)


def test_guidelines_expose_risk_behaviors_and_examples(client):
    body = client.get("/assistant/guidelines").json()
    assert len(body["risk_behaviors"]) == 5
    assert any("SAMU (192)" in item for item in body["risk_behaviors"])
    assert all(q["example_good"] and q["example_bad"] for q in body["voice_questions"])


def test_pronouns_accept_only_known_options(client, db):
    _cleanup(db)
    client.post("/professionals", json={"slug": TEST_SLUG, "name": "Teste Cadastro", "pronouns": "masculine"})
    assert client.get(f"/professionals/{TEST_SLUG}").json()["pronouns"] == "masculine"
    assert client.patch(f"/professionals/{TEST_SLUG}", json={"pronouns": "outro"}).status_code == 422
    options = client.get("/assistant/guidelines").json()["pronoun_options"]
    assert [o["key"] for o in options] == ["feminine", "masculine", "neutral"]
    _cleanup(db)
