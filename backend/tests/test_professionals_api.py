from app import models

TEST_SLUG = "test-pytest-professional"


def _cleanup(db):
    db.query(models.Professional).filter_by(slug=TEST_SLUG).delete()
    db.commit()


def test_create_get_and_reject_duplicate_professional(client, db):
    _cleanup(db)

    response = client.post(
        "/professionals",
        json={"slug": TEST_SLUG, "name": "Teste Pytest", "voice_tone": "direto"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["slug"] == TEST_SLUG
    assert body["name"] == "Teste Pytest"

    response = client.get(f"/professionals/{TEST_SLUG}")
    assert response.status_code == 200
    assert response.json()["slug"] == TEST_SLUG

    response = client.post(
        "/professionals",
        json={"slug": TEST_SLUG, "name": "Outro Nome"},
    )
    assert response.status_code == 409

    _cleanup(db)


def test_get_unknown_professional_returns_404(client):
    response = client.get("/professionals/slug-que-nao-existe-123")
    assert response.status_code == 404


def test_create_professional_rejects_uppercase_slug(client):
    response = client.post(
        "/professionals",
        json={"slug": "Nao-Pode-Maiuscula", "name": "Teste"},
    )
    assert response.status_code == 422


def test_update_assistant_profile_and_reject_unknown_question(client, db):
    _cleanup(db)
    client.post("/professionals", json={"slug": TEST_SLUG, "name": "Teste Pytest"})

    response = client.patch(
        f"/professionals/{TEST_SLUG}",
        json={
            "service_info": "R$ 200 a sessão.",
            "voice_examples": {"preco": {"good": "Custa R$ 200.", "bad": "Depende."}},
            "extra_never_say": ["Falar de política.", "   "],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["service_info"] == "R$ 200 a sessão."
    assert body["voice_examples"]["preco"]["good"] == "Custa R$ 200."
    assert body["extra_never_say"] == ["Falar de política."]

    response = client.patch(
        f"/professionals/{TEST_SLUG}",
        json={"voice_examples": {"pergunta-inventada": {"good": "x", "bad": "y"}}},
    )
    assert response.status_code == 422

    _cleanup(db)


def test_guidelines_expose_fixed_rules(client):
    response = client.get("/assistant/guidelines")
    assert response.status_code == 200
    body = response.json()
    assert body["assistant_name"] == "SelenIA"
    assert [q["key"] for q in body["voice_questions"]] == ["preco", "funcionamento", "momento_dificil"]
    assert len(body["never_say"]) > 0
