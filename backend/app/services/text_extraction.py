import io

from docx import Document as DocxDocument
from pypdf import PdfReader


def extract_text(filename: str, content: bytes) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if lower.endswith(".docx"):
        doc = DocxDocument(io.BytesIO(content))
        return "\n".join(paragraph.text for paragraph in doc.paragraphs)
    return content.decode("utf-8", errors="ignore")


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    normalized = " ".join(text.split())
    if not normalized:
        return []

    chunks = []
    start = 0
    while start < len(normalized):
        end = start + chunk_size
        chunks.append(normalized[start:end])
        start = end - overlap
    return chunks
