"""
Validador único: roda TODOS os impostos (federal/estadual/municipal) numa tacada.
Se já existirem regras específicas em módulos legados, plugue aqui dentro.
NÃO quebra o fluxo se algo faltar: devolve estrutura canônica.
"""

from typing import Dict, Any
from validador_fiscal.taxes.matriz_loader import load_matriz
from validador_fiscal.taxes.legacy_engine import calcular_legados
from validador_fiscal.taxes.cbs_client import CBSCalculatorClient


def _r2(x):
    try:
        return round(float(x), 2)
    except Exception:
        return 0.0


def validate_all(nf, usar_cbs_oficial: bool = True) -> Dict[str, Any]:
    # Estrutura canônica
    calculados = {
        "icms": 0.0, "st": 0.0, "difal": 0.0, "ipi": 0.0,
        "pis": 0.0, "cofins": 0.0, "iss": 0.0,
        "irpj": 0.0, "csll": 0.0,
        "cbs": 0.0, "ibs": 0.0, "is_": 0.0,
    }
    divergencias, etapas = [], []

    # Valor base para fallback mínimo
    total_itens = 0.0
    for it in getattr(nf, "itens", []) or []:
        total_itens += float(getattr(it, "valor_total", 0) or 0)

    # 1) LEGADOS via MATRIZ (motor oficial seu)
    try:
        matriz = load_matriz()
        calc_leg, meta = calcular_legados(nf, matriz)
        cd = calc_leg.dict()
        for k in ("icms","st","difal","ipi","pis","cofins","iss","irpj","csll"):
            calculados[k] = _r2(cd.get(k, 0.0))
        etapas.append({"etapa": "legados.matriz", "ts": None, "meta": meta})
    except Exception:
        calculados["pis"] = _r2(total_itens * 0.0165) if total_itens else 0.0
        calculados["cofins"] = _r2(total_itens * 0.076) if total_itens else 0.0
        etapas.append({"etapa": "legados.fallback_minimo", "ts": None})

    # 2) CBS/IBS/IS (API oficial)
    if usar_cbs_oficial:
        try:
            cli = CBSCalculatorClient()
            nf_dict = nf.dict() if hasattr(nf, "dict") else nf.__dict__
            payload = cli.mapear_payload(nf_dict)
            resp = cli.calcular_regime_geral(payload)
            calculados["cbs"] = _r2(resp.get("cbs", resp.get("valor_cbs", 0.0)))
            calculados["ibs"] = _r2(resp.get("ibs", resp.get("valor_ibs", 0.0)))
            calculados["is_"] = _r2(resp.get("is",  resp.get("valor_is",  0.0)))
            etapas.append({"etapa": "cbs_ibs_is.api_oficial", "ts": None, "ok": True})
        except Exception as e:
            etapas.append({"etapa": "cbs_ibs_is.api_oficial", "ts": None, "ok": False, "erro": str(e)})

    # Finalização
    etapas.append({"etapa": "legados_minimos", "ts": None})
    return {"calculados": calculados, "divergencias": divergencias, "etapas": etapas}
