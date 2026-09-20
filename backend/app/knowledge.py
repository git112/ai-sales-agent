from __future__ import annotations

import re
from pathlib import Path

from app.core.config import settings
from app.store import get_by_id, update_record

UPLOAD_ROOT = Path(__file__).resolve().parent.parent / "uploads"


def extract_text(path: Path, suffix: str) -> str:
    suffix = suffix.lower()
    if suffix == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if suffix in (".docx", ".doc"):
        import docx

        d = docx.Document(str(path))
        return "\n".join(p.text for p in d.paragraphs)
    raise ValueError("Unsupported file type")


def chunk_text(text: str, size: int = 500) -> list[str]:
    words = text.split()
    chunks = []
    for i in range(0, len(words), size):
        chunk = " ".join(words[i : i + size]).strip()
        if chunk:
            chunks.append(chunk)
    return chunks or [text[:2000]]


class KnowledgeStore:
    def __init__(self) -> None:
        self._chroma = None

    def _client(self):
        if self._chroma is not False and self._chroma is None:
            try:
                import chromadb

                path = Path(settings.chroma_path)
                if not path.is_absolute():
                    path = Path(__file__).resolve().parent.parent / path
                path.mkdir(parents=True, exist_ok=True)
                self._chroma = chromadb.PersistentClient(path=str(path))
            except Exception:
                self._chroma = False
        return self._chroma if self._chroma is not False else None

    def index_document(self, doc: dict, text: str) -> int:
        chunks = chunk_text(text)
        client = self._client()
        if client:
            col = client.get_or_create_collection(f"ws_{doc['workspace_id']}")
            ids = [f"{doc['id']}_{i}" for i in range(len(chunks))]
            col.upsert(ids=ids, documents=chunks, metadatas=[{"doc_id": doc["id"]} for _ in chunks])
        update_record("knowledge_documents", doc["id"], {"chunk_count": len(chunks), "extracted_text": text, "status": "ready"})
        return len(chunks)

    def search(self, workspace_id: str, query: str, doc_ids: list[str] | None = None) -> list[str]:
        client = self._client()
        if client:
            try:
                col = client.get_or_create_collection(f"ws_{workspace_id}")
                res = col.query(query_texts=[query], n_results=4)
                docs = (res.get("documents") or [[]])[0]
                metas = (res.get("metadatas") or [[]])[0]
                out = []
                for d, m in zip(docs, metas):
                    if doc_ids and m.get("doc_id") not in doc_ids:
                        continue
                    out.append(d)
                if out:
                    return out
            except Exception:
                pass
        # keyword fallback
        from app.store import by_workspace

        q_terms = [t for t in re.split(r"\W+", query.lower()) if t]
        ranked = []
        for doc in by_workspace("knowledge_documents", workspace_id):
            if doc_ids and doc["id"] not in doc_ids:
                continue
            text = doc.get("extracted_text") or ""
            score = sum(text.lower().count(t) for t in q_terms)
            if score:
                ranked.append((score, text[:800]))
        ranked.sort(reverse=True)
        return [t for _, t in ranked[:4]]


knowledge_store = KnowledgeStore()
