# validador_fiscal/rag/chroma_manager.py
import os, hashlib
from typing import Optional, List
from chromadb import Client
from chromadb.config import Settings

_DEF_PATH = os.path.join("data", "vectorstore")
os.makedirs(_DEF_PATH, exist_ok=True)

def _client(persist_dir: Optional[str] = None) -> Client:
    persist_dir = persist_dir or _DEF_PATH
    os.makedirs(persist_dir, exist_ok=True)
    return Client(Settings(persist_directory=persist_dir, anonymized_telemetry=False))

def get_or_create_collection(name: str = "relatorios", persist_dir: Optional[str] = None):
    cli = _client(persist_dir)
    try:
        return cli.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})
    except Exception:
        # compat antigas
        return cli.get_or_create_collection(name=name)

def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def upsert_report_text(collection, path_report: str) -> str:
    """Idempotente: reindexa o mesmo arquivo sempre com o mesmo id."""
    text = _read_text(path_report)
    doc_id = hashlib.sha1(path_report.encode("utf-8")).hexdigest()
    collection.upsert(ids=[doc_id], documents=[text], metadatas=[{"path": path_report}])
    return doc_id

def retriever_from_report(path_report: str, persist_dir: Optional[str] = None):
    """Retorna um callable retriever(query)->list[str]."""
    col = get_or_create_collection("relatorios", persist_dir=persist_dir)
    upsert_report_text(col, path_report)

    def _retriever(query: str, k: int = 4) -> List[str]:
        res = col.query(query_texts=[query], n_results=k)
        docs = res.get("documents") or [[]]
        return docs[0]
    return _retriever

