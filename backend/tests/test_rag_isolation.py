"""Base de conhecimento: o material de uma profissional nunca chega à outra.

Usa um ChromaDB de verdade numa pasta temporária, com uma função de
embedding simples (contagem de palavras), para não baixar modelo nem
depender da base local. O isolamento testado é o do código: uma coleção
por profissional, escolhida pelo slug da conversa.
"""

import hashlib
import math

import chromadb
import pytest
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

from app import models
from app.services import llm, rag

SLUG_A = "test-rag-isolamento-a"
SLUG_B = "test-rag-isolamento-b"
# Um slug que começa igual ao de A, para conferir que não há busca por prefixo.
SLUG_A2 = "test-rag-isolamento-a-2"

TEXTO_A = "Marina atende casais em Niterói. A sessão de casal custa duzentos e noventa reais."
TEXTO_B = "Bianca atende adolescentes em Curitiba. A sessão individual custa cento e vinte reais."
TEXTO_A2 = "Material de outra conta com slug parecido: atendimento de grupos aos sábados."


class _ContagemDePalavras(EmbeddingFunction):
    """Embedding determinístico: cada palavra soma 1 numa de 64 posições."""

    def __init__(self):
        pass

    def __call__(self, input: Documents) -> Embeddings:
        vetores = []
        for texto in input:
            v = [0.0] * 64
            for palavra in texto.lower().split():
                v[int(hashlib.md5(palavra.encode()).hexdigest(), 16) % 64] += 1.0
            norma = math.sqrt(sum(x * x for x in v)) or 1.0
            vetores.append([x / norma for x in v])
        return vetores

    @staticmethod
    def name() -> str:
        return "contagem-de-palavras-teste"

    def get_config(self):
        return {}

    @staticmethod
    def build_from_config(config):
        return _ContagemDePalavras()


@pytest.fixture
def chroma_temporario(tmp_path, monkeypatch):
    monkeypatch.setattr(rag, "_client", chromadb.PersistentClient(path=str(tmp_path / "chroma")))
    monkeypatch.setattr(rag, "_embedding_fn", _ContagemDePalavras())


def _apagar_profissionais(db):
    for slug in (SLUG_A, SLUG_B):
        professional = db.query(models.Professional).filter_by(slug=slug).first()
        if professional:
            db.delete(professional)
    db.commit()


def test_query_of_one_professional_never_returns_another_ones_chunks(chroma_temporario):
    rag.add_chunks(SLUG_A, "doc-a", "a.txt", [TEXTO_A, "Marina não atende por plano de saúde."])
    rag.add_chunks(SLUG_B, "doc-b", "b.txt", [TEXTO_B, "Bianca atende por plano de saúde."])
    rag.add_chunks(SLUG_A2, "doc-a2", "a2.txt", [TEXTO_A2])

    # A pergunta copia o texto de B palavra por palavra: na busca de A, o
    # trecho de B seria o mais parecido se as coleções se misturassem.
    trechos_a, metadados_a = rag.query(SLUG_A, TEXTO_B, top_k=10)
    assert trechos_a and all("Bianca" not in t and "grupos" not in t for t in trechos_a)
    assert {m["document_id"] for m in metadados_a} == {"doc-a"}

    trechos_b, metadados_b = rag.query(SLUG_B, TEXTO_A, top_k=10)
    assert trechos_b and all("Marina" not in t and "grupos" not in t for t in trechos_b)
    assert {m["document_id"] for m in metadados_b} == {"doc-b"}

    assert rag.query("test-rag-isolamento-sem-documentos", TEXTO_A) == ([], [])

    # Apagar o documento de A não mexe no de B.
    rag.delete_document(SLUG_A, "doc-a")
    assert rag.query(SLUG_A, TEXTO_A) == ([], [])
    assert rag.query(SLUG_B, TEXTO_B)[1][0]["document_id"] == "doc-b"


def test_reply_prompt_only_carries_the_professionals_own_documents(chroma_temporario, client, db, monkeypatch):
    _apagar_profissionais(db)
    prompts = []

    def resposta_falsa(system_prompt, history, **_):
        prompts.append(system_prompt)
        return "resposta de teste"

    monkeypatch.setattr(llm, "generate_reply", resposta_falsa)
    try:
        for slug, nome, texto in ((SLUG_A, "Marina Teste", TEXTO_A), (SLUG_B, "Bianca Teste", TEXTO_B)):
            client.post("/professionals", json={"slug": slug, "name": nome})
            enviado = client.post(
                "/documents/upload",
                data={"professional_slug": slug},
                files={"file": ("material.txt", texto.encode(), "text/plain")},
            )
            assert enviado.status_code == 201

        # Conversa com B perguntando exatamente o que está no material de A.
        resposta = client.post(
            "/chat/simulate", json={"professional_slug": SLUG_B, "message": "quanto custa a sessão de casal em Niterói?"}
        )
        assert resposta.status_code == 200
        assert prompts, "a resposta do modelo não foi chamada"
        assert "Bianca atende adolescentes" in prompts[-1]
        assert "Marina" not in prompts[-1] and "Niterói. A sessão de casal" not in prompts[-1]
    finally:
        _apagar_profissionais(db)
