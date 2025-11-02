# validador_fiscal/agents/tax_engine_agent.py
"""
Motor Fiscal - CSV usa código original, XML usa IA
"""
from typing import Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

try:
    from validador_fiscal.core.models import NotaFiscal as NotaFiscalPydantic
    USE_PYDANTIC = True
except:
    USE_PYDANTIC = False

from validador_fiscal.taxes.legacy_engine import calcular_legados_item_a_item
from validador_fiscal.taxes.matriz_loader import load_matriz

# Importar IA
try:
    from validador_fiscal.agents import fiscal_ai_agent
    HAS_AI = True
    print("✅ Agente IA importado com sucesso")
except Exception as e:
    HAS_AI = False
    print(f"❌ Erro importando agente IA: {e}")

MAX_WORKERS = 4
CHUNK_SIZE = 10000

def run(nf, usar_cbs_oficial: bool = True) -> Dict[str, Any]:
    """
    Calcula impostos:
    - CSV: Sistema original (paralelo, chunks)
    - XML: IA valida e calcula
    """
    
    # Verificar se tem declarados (XML)
    tem_declarados = hasattr(nf, 'declarados') and nf.declarados is not None
    
    # XML com poucos itens → IA
    print(f"   🔍 DEBUG: tem_declarados={tem_declarados}, itens={len(nf.itens)}, HAS_AI={HAS_AI}")
    if tem_declarados and len(nf.itens) < 20 and HAS_AI:
        print(f"   🤖 XML ({len(nf.itens)} itens) → IA calculando...")
        
        try:
            matriz = load_matriz()
            totais_ia, analise_ia = fiscal_ai_agent.calcular_e_validar_xml(nf, matriz)
            
            # Formatar resposta
            return {
                "calculados": totais_ia,
                "linhas": [],
                "etapas": {
                    "legados": f"IA analisou {len(nf.itens)} itens",
                    "cbs": "N/A (XML)"
                },
                "analise_ia": analise_ia  # AQUI ESTÁ A ANÁLISE DA IA!
            }
            
        except Exception as e:
            print(f"   ⚠️ Erro IA: {e}. Usando sistema padrão...")
    
    # CSV ou fallback → SISTEMA ORIGINAL (NÃO MEXE!)
    print(f"   📊 CSV ({len(nf.itens)} itens) → Sistema original...")
    
    matriz = load_matriz()
    itens = nf.itens if hasattr(nf, 'itens') else []
    
    # Processar em paralelo (código original)
    chunks = [itens[i:i + CHUNK_SIZE] for i in range(0, len(itens), CHUNK_SIZE)]
    
    all_lines = []
    totais = {
        "icms": 0, "st": 0, "difal": 0, "ipi": 0,
        "pis": 0, "cofins": 0, "iss": 0, "irpj": 0, "csll": 0
    }
    
    def process_chunk(chunk):
        chunk_totais = {k: 0 for k in totais.keys()}
        chunk_lines = []
        
        for item in chunk:
            result = calcular_legados_item_a_item(item, matriz)
            
            for imp in totais.keys():
                if imp in result:
                    chunk_totais[imp] += result[imp]
            
            chunk_lines.append(result)
        
        return chunk_totais, chunk_lines
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(process_chunk, chunk) for chunk in chunks]
        
        for future in as_completed(futures):
            chunk_totais, chunk_lines = future.result()
            
            for imp in totais.keys():
                totais[imp] += chunk_totais[imp]
            
            all_lines.extend(chunk_lines)
    
    return {
        "calculados": totais,
        "linhas": all_lines,
        "etapas": {
            "legados": f"{len(itens)} itens processados",
            "cbs": "CBS/IBS desabilitado" if not usar_cbs_oficial else "N/A"
        }
    }