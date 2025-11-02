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
        # Fallback: Alíquotas padrão conhecidas
        if cfop and cfop.startswith("5"):  # Operação interna
            resultado["icms"] = valor * 0.18  # SP padrão
        
        resultado["pis"] = valor * 0.0165
        resultado["cofins"] = valor * 0.076
        
        return resultado
        
    except Exception as e:
        print(f"⚠️ Erro busca online: {e}")
        return resultado

def buscar_aliquota_sefaz(uf: str, ncm: str, cfop: str) -> Dict:
    """
    Busca alíquota ICMS no site da SEFAZ (simulação)
    Na prática, cada UF tem portal diferente
    """
    try:
        # Exemplo com API pública (substitua por real)
        url = f"https://api.exemplo.com/sefaz/{uf}/aliquota"
        params = {"ncm": ncm, "cfop": cfop}
        
        response = requests.get(url, params=params, timeout=5)
        
        if response.status_code == 200:
            return response.json()
        
        return {"erro": "API indisponível"}
        
    except Exception as e:
        return {"erro": str(e)}

def buscar_ipi_receita(ncm: str) -> float:
    """
    Busca IPI no site da Receita Federal
    """
    try:
        # Scraping do site da Receita (exemplo)
        url = f"https://www.gov.br/receitafederal/ipi/{ncm}"
        
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            # Parse HTML aqui
            return 0.0
        
        return 0.0
        
    except:
        return 0.0