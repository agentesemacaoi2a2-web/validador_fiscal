import requests
from typing import Dict

def buscar_impostos_online(ncm: str, cfop: str, uf_origem: str, uf_destino: str, valor: float) -> Dict:
    """
    Busca alíquotas em APIs públicas/comerciais
    """
    resultado = {
        "icms": 0.0,
        "pis": 0.0,
        "cofins": 0.0,
        "ipi": 0.0,
        "fonte": "api_externa"
    }
    
    try:
        # API 1: BrasilAPI (gratuita, NCM)
        url_ncm = f"https://brasilapi.com.br/api/ncm/v1/{ncm}"
        resp = requests.get(url_ncm, timeout=5)
        
        if resp.status_code == 200:
            dados_ncm = resp.json()
            # Extrair IPI se disponível
            
        # API 2: TaxWeb ou similar (comercial, precisa key)
        # url_tax = f"https://api.taxweb.com.br/calculo"
        # payload = {"ncm": ncm, "cfop": cfop, "uf": uf_origem}
        # resp = requests.post(url_tax, json=payload, headers={"Authorization": "Bearer KEY"})
        
        # Fallback: Alíquotas padrão conhecidas
        if cfop.startswith("5"):  # Operação interna
            resultado["icms"] = valor * 0.18  # SP padrão
        
        resultado["pis"] = valor * 0.0165
        resultado["cofins"] = valor * 0.076
        
        return resultado
        
    except Exception as e:
        print(f"⚠️ Erro busca online: {e}")
        return resultado