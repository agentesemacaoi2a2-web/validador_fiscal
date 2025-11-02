# validador_fiscal/tools/rag_tool.py
from typing import List, Tuple

def rag_query(question: str, retriever) -> Tuple[str, List[str]]:
    """
    Recebe uma pergunta e um retriever(query)->List[str].
    Retorna (answer, sources). Sem LLM: junta top docs como resposta.
    """
    sources = retriever(question) if retriever else []
    if not sources:
        return ("Não encontrei base indexada ainda. Gere o relatório primeiro.", [])

    joined = "\n---\n".join(sources[:3])
    answer = f"Resposta com base nos trechos recuperados:\n{joined[:1500]}"
    return (answer, sources)



