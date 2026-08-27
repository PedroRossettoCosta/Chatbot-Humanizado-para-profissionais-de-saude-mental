import re

import chromadb
from chromadb.utils import embedding_functions

from app.config import settings

_client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
_embedding_fn = embedding_functions.DefaultEmbeddingFunction()


def _collection_name(slug: str) -> str:
    safe = re.sub(r"[^a-z0-9-]", "-", slug.lower())
    return f"prof-{safe}"


def get_collection(slug: str):
    return _client.get_or_create_collection(
        name=_collection_name(slug),
        embedding_function=_embedding_fn,
    )


def add_chunks(slug: str, document_id: str, filename: str, chunks: list[str]) -> None:
    if not chunks:
        return

    collection = get_collection(slug)
    ids = [f"{document_id}-{i}" for i in range(len(chunks))]
    metadatas = [
        {"document_id": document_id, "filename": filename, "chunk_index": i} for i in range(len(chunks))
    ]
    collection.add(ids=ids, documents=chunks, metadatas=metadatas)


def query(slug: str, text: str, top_k: int = 4) -> tuple[list[str], list[dict]]:
    collection = get_collection(slug)
    count = collection.count()
    if count == 0:
        return [], []

    results = collection.query(query_texts=[text], n_results=min(top_k, count))
    documents = results.get("documents") or [[]]
    metadatas = results.get("metadatas") or [[]]
    return documents[0], metadatas[0]
