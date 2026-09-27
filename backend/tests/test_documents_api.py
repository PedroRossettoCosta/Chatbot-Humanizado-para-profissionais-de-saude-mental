"""Base de conhecimento: envio e remoção de documento.

O ChromaDB é substituído: aqui interessa o registro no banco e a
chamada certa para apagar os trechos.
"""

from app import models
from app.services import rag

TEST_SLUG = "test-pytest-documentos"


def _cleanup(db):
    db.query(models.Document).filter(
        models.Document.professional_id.in_(db.query(models.Professional.id).filter_by(slug=TEST_SLUG))
    ).delete(synchronize_session=False)
    db.query(models.Professional).filter_by(slug=TEST_SLUG).delete()
    db.commit()


def test_upload_then_delete_removes_record_and_chunks(client, db, monkeypatch):
    _cleanup(db)
    deleted = []
    monkeypatch.setattr(rag, "add_chunks", lambda *args: None)
    monkeypatch.setattr(rag, "delete_document", lambda slug, document_id: deleted.append((slug, document_id)))
    client.post("/professionals", json={"slug": TEST_SLUG, "name": "Teste Documentos"})

    response = client.post(
        "/documents/upload",
        data={"professional_slug": TEST_SLUG},
        files={"file": ("perguntas.txt", "Como funciona a primeira sessão?".encode(), "text/plain")},
    )
    assert response.status_code == 201
    document_id = response.json()["id"]

    assert client.delete(f"/documents/{document_id}").status_code == 204
    assert deleted == [(TEST_SLUG, document_id)]
    assert client.get(f"/documents/{TEST_SLUG}").json() == []
    assert client.delete(f"/documents/{document_id}").status_code == 404
    _cleanup(db)
