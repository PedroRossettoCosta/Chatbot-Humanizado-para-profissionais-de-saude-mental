from app import models
from app.services import llm

TEST_SLUG = "test-pytest-chat"


def _cleanup(db):
    professional = db.query(models.Professional).filter_by(slug=TEST_SLUG).first()
    if professional:
        db.delete(professional)
        db.commit()


def test_first_message_includes_disclaimer_and_second_does_not(client, db, monkeypatch):
    _cleanup(db)
    monkeypatch.setattr(llm, "generate_reply", lambda system_prompt, history: "resposta de teste")

    professional = models.Professional(slug=TEST_SLUG, name="Teste Chat")
    db.add(professional)
    db.commit()

    r1 = client.post("/chat/simulate", json={"professional_slug": TEST_SLUG, "message": "oi"})
    assert r1.status_code == 200
    body1 = r1.json()
    assert body1["disclaimer"] is not None
    assert "inteligência artificial" in body1["disclaimer"]

    r2 = client.post(
        "/chat/simulate",
        json={
            "professional_slug": TEST_SLUG,
            "message": "segunda mensagem",
            "session_id": body1["session_id"],
        },
    )
    assert r2.status_code == 200
    assert r2.json()["disclaimer"] is None

    _cleanup(db)
