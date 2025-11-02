# validador_fiscal/core/utils.py
# Utilitários consolidados. Mantém nomes antigos e novos como aliases para compatibilidade.
from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from typing import Dict, Any

def to_float(x) -> float:
    try:
        s = str(x).strip().replace(",", ".").replace("%", "")
        return float(s)
    except Exception:
        return 0.0

# alias para compat com versões antigas que usavam _to_float
_to_float = to_float

def round2(x: Any) -> float:
    try:
        return float(Decimal(float(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    except Exception:
        try:
            return float(x or 0.0)
        except Exception:
            return 0.0

# alias para compat com _round2
_round2 = round2

def ts() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"

# alias
_ts = ts

def sum_por_imposto(tot: Dict[str, float]) -> Dict[str, float]:
    m = {
        "icms": "icms", "st": "st", "difal": "difal", "ipi": "ipi",
        "pis": "pis", "cofins": "cofins", "iss": "iss",
        "irpj": "irpj", "csll": "csll", "cbs": "cbs", "ibs": "ibs", "is": "is_",
    }
    saida = {v: _round2(tot.get(k, 0.0)) for k, v in m.items()}
    # garante todas as chaves presentes
    for v in ["icms","st","difal","ipi","pis","cofins","iss","irpj","csll","cbs","ibs","is_"]:
        saida.setdefault(v, 0.0)
    return saida

# alias antigo
_sum_por_imposto = sum_por_imposto
