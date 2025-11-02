from typing import Dict, Any, List

def _r2(v):
    try: return round(float(v), 2)
    except: return 0.0

def run(resultado: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Compara valores declarados vs calculados.
    """
    diverg = []
    nf = resultado.get("nf") or {}
    declarados = (nf.get("declarados") or {}) if isinstance(nf, dict) else {}
    calculados = resultado.get("calculados") or {}

    for imp, vcalc in calculados.items():
        vdec = declarados.get(imp)
        if vdec is None:
            continue
        diff = _r2(vcalc) - _r2(vdec)
        if abs(diff) >= 0.01:
            diverg.append({
                "imposto": imp.upper(),
                "declarado": _r2(vdec),
                "calculado": _r2(vcalc),
                "diferenca": _r2(diff),
            })

    return diverg
