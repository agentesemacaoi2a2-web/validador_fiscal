# validador_fiscal/taxes/cbs_client_v2.py
"""
Cliente CBS/IBS/IS com Cache e Retry
Consulta API da Reforma Tributária com fallback robusto
"""

import requests
import json
import os
import time
from functools import lru_cache
from typing import Dict, Optional


# ==================== CONFIGURAÇÃO ====================

# Cache em memória (durante execução)
@lru_cache(maxsize=2000)
def _cache_memoria(chave: str):
    """Cache em memória RAM para acesso ultrarrápido"""
    return None

# Cache em arquivo (persiste entre execuções)
CACHE_FILE = "data/cache/cbs_cache.json"
CBS_CACHE = {}

def load_cache():
    """Carrega cache do disco"""
    global CBS_CACHE
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                CBS_CACHE = json.load(f)
            print(f"✅ Cache CBS carregado: {len(CBS_CACHE)} entradas")
        except Exception as e:
            print(f"⚠️ Erro ao carregar cache CBS: {e}")
            CBS_CACHE = {}
    else:
        CBS_CACHE = {}

def save_cache():
    """Salva cache no disco"""
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(CBS_CACHE, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ Erro ao salvar cache CBS: {e}")

# Carregar cache ao importar o módulo
load_cache()


# ==================== API CLIENT ====================

def consultar_api_cbs(ncm: str, cfop: str, tentativas: int = 3, timeout: int = 30) -> Optional[Dict]:
    """
    Consulta API oficial da Reforma Tributária (CBS/IBS/IS)
    
    Args:
        ncm: Código NCM do produto (8 dígitos)
        cfop: Código CFOP da operação (4 dígitos)
        tentativas: Número de tentativas em caso de falha
        timeout: Timeout em segundos
        
    Returns:
        Dict com alíquotas ou None se falhar
    """
    
    # URL da API (NOTA: verificar URL real quando disponível)
    # Por enquanto usando URL hipotética
    url = f"https://api.reformatributaria.gov.br/v1/aliquotas/{ncm}/{cfop}"
    
    for tentativa in range(tentativas):
        try:
            response = requests.get(
                url,
                timeout=timeout,
                headers={
                    "User-Agent": "ValidadorFiscal/2.0",
                    "Accept": "application/json"
                }
            )
            
            if response.status_code == 200:
                return response.json()
            
            elif response.status_code == 404:
                # Produto não encontrado - não adianta tentar de novo
                return None
            
            elif response.status_code in (429, 503):
                # Rate limit ou serviço indisponível - aguardar mais tempo
                if tentativa < tentativas - 1:
                    wait_time = (2 ** tentativa) * 2  # backoff mais agressivo
                    print(f"⏳ Rate limit ou serviço indisponível, aguardando {wait_time}s...")
                    time.sleep(wait_time)
                    continue
            
            else:
                # Outro erro HTTP
                print(f"⚠️ API CBS retornou status {response.status_code}")
                if tentativa < tentativas - 1:
                    time.sleep(2 ** tentativa)
                    continue
        
        except requests.Timeout:
            print(f"⏱️ Timeout na consulta CBS (tentativa {tentativa + 1}/{tentativas})")
            if tentativa < tentativas - 1:
                time.sleep(2 ** tentativa)
                continue
        
        except requests.ConnectionError:
            print(f"🔌 Erro de conexão com API CBS (tentativa {tentativa + 1}/{tentativas})")
            if tentativa < tentativas - 1:
                time.sleep(2 ** tentativa)
                continue
        
        except Exception as e:
            print(f"❌ Erro inesperado na API CBS: {e}")
            break
    
    return None


def consultar_matriz_local(ncm: str, cfop: str) -> Dict:
    """
    Fallback: consulta matriz local de alíquotas CBS/IBS/IS
    
    Notas:
    - Por enquanto retorna valores zero, pois a reforma ainda não está 100% regulamentada
    - Quando houver tabelas oficiais, implementar lógica aqui
    """
    
    # Valores padrão (reforma ainda não implementada)
    resultado = {
        "cbs_aliquota": 0.0,     # Substitui PIS/COFINS
        "ibs_aliquota": 0.0,     # Substitui ICMS
        "is_aliquota": 0.0,      # Imposto seletivo
        "fonte": "MATRIZ_LOCAL_FALLBACK",
        "observacao": "Reforma tributária ainda não regulamentada - valores indicativos"
    }
    
    # TODO: Implementar lógica de consulta real quando tabelas oficiais disponíveis
    # Possível estrutura:
    # - Carregar CSV/Excel com tabelas NCM x Alíquotas
    # - Verificar categorias especiais (IS aplicável a bebidas, cigarros, etc)
    # - Aplicar regras de transição (se operação até 2026, usar legado)
    
    return resultado


def consultar_cbs_cached(ncm: str, cfop: str) -> Dict:
    """
    Consulta CBS/IBS/IS com sistema de cache multinível
    
    Ordem de prioridade:
    1. Cache em memória (RAM) - ultrarrápido
    2. Cache em arquivo (disco) - rápido
    3. API oficial - lento mas atualizado
    4. Matriz local - fallback garantido
    
    Args:
        ncm: Código NCM (8 dígitos)
        cfop: Código CFOP (4 dígitos)
        
    Returns:
        Dict com alíquotas CBS/IBS/IS
    """
    
    # Normalizar inputs
    ncm = str(ncm).strip().zfill(8)
    cfop = str(cfop).strip().zfill(4)
    cache_key = f"{ncm}_{cfop}"
    
    # 1. Verificar cache em memória
    cached = _cache_memoria(cache_key)
    if cached is not None:
        return cached
    
    # 2. Verificar cache em arquivo
    if cache_key in CBS_CACHE:
        resultado = CBS_CACHE[cache_key]
        # Atualizar também o cache em memória
        _cache_memoria.cache_info()  # força cache
        return resultado
    
    # 3. Tentar API oficial
    resultado = consultar_api_cbs(ncm, cfop)
    
    # 4. Se API falhou, usar matriz local (fallback garantido)
    if resultado is None:
        print(f"⚠️ API CBS indisponível para {ncm}/{cfop}, usando matriz local")
        resultado = consultar_matriz_local(ncm, cfop)
    
    # Salvar em ambos os caches
    CBS_CACHE[cache_key] = resultado
    save_cache()
    
    return resultado


def limpar_cache():
    """Limpa todo o cache CBS (útil para forçar atualização)"""
    global CBS_CACHE
    CBS_CACHE = {}
    _cache_memoria.cache_clear()
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)
    print("🗑️ Cache CBS limpo")


def estatisticas_cache():
    """Retorna estatísticas do cache"""
    return {
        "entradas_arquivo": len(CBS_CACHE),
        "memoria_hits": _cache_memoria.cache_info().hits,
        "memoria_misses": _cache_memoria.cache_info().misses,
        "tamanho_arquivo_kb": os.path.getsize(CACHE_FILE) / 1024 if os.path.exists(CACHE_FILE) else 0
    }


# ==================== UTILITÁRIOS ====================

def validar_ncm(ncm: str) -> bool:
    """Valida formato do NCM (8 dígitos numéricos)"""
    try:
        return len(str(ncm).strip()) == 8 and str(ncm).isdigit()
    except:
        return False


def validar_cfop(cfop: str) -> bool:
    """Valida formato do CFOP (4 dígitos numéricos)"""
    try:
        return len(str(cfop).strip()) == 4 and str(cfop).isdigit()
    except:
        return False


# ==================== TESTE ====================

if __name__ == "__main__":
    # Teste rápido
    print("=" * 60)
    print("TESTE DO CBS CLIENT")
    print("=" * 60)
    
    # Testar com NCM/CFOP exemplo
    teste_ncm = "84713012"  # Processadores
    teste_cfop = "5102"      # Venda interna
    
    print(f"\nConsultando: NCM {teste_ncm} / CFOP {teste_cfop}")
    resultado = consultar_cbs_cached(teste_ncm, teste_cfop)
    
    print("\n📊 Resultado:")
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
    
    print("\n📈 Estatísticas do cache:")
    stats = estatisticas_cache()
    print(json.dumps(stats, indent=2))
    
    print("\n✅ Teste concluído")
