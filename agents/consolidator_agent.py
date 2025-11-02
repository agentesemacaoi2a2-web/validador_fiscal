from typing import Dict, Any
from copy import deepcopy

def run(nf: Any, taxes: Dict[str, Any]) -> Dict[str, Any]:
    """
    Consolida o resultado para as próximas etapas e para Excel.
    """
    # Passar total_produtos correto (com desconto)
    total_produtos = getattr(nf, "total_produtos", None)
    if not total_produtos:
        total_produtos = sum(getattr(item, "valor_total", 0) for item in getattr(nf, "itens", []))
    
    return {
        "nf": getattr(nf, "dict", lambda: nf)(),
        "calculados": deepcopy(taxes.get("calculados", {})),
        "linhas": taxes.get("linhas", []),  # detalhamento item a item (se houver)
        "etapas": taxes.get("etapas", []),
        "total_produtos": total_produtos,
    }