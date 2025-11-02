# validador_fiscal/agents/tax_engine_agent.py
"""
Motor Fiscal - CSV usa código vetorizado, XML usa IA
"""
from typing import Dict, Any
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


def run(nf, usar_cbs_oficial: bool = True) -> Dict[str, Any]:
    """
    Calcula impostos:
    - CSV: Sistema vetorizado (100x mais rápido)
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
                "analise_ia": analise_ia
            }
            
        except Exception as e:
            print(f"   ⚠️ Erro IA: {e}. Usando sistema padrão...")
    
    # CSV → SISTEMA VETORIZADO (calcula tudo de uma vez com pandas)
    print(f"   📊 CSV ({len(nf.itens)} itens) → Sistema vetorizado...")
    
    matriz = load_matriz()
    itens = nf.itens if hasattr(nf, 'itens') else []
    
    if not itens:
        return {
            "calculados": {"icms": 0, "st": 0, "difal": 0, "ipi": 0, "pis": 0, "cofins": 0, "iss": 0, "irpj": 0, "csll": 0},
            "linhas": [],
            "etapas": {"legados": "Nenhum item", "cbs": "N/A"}
        }
    
    # ⚡ OTIMIZAÇÃO: Chamar calcular_legados_item_a_item UMA VEZ com TODA a nota
    # (função já está vetorizada internamente com pandas)
    print(f"   ⏱️  Processando {len(itens):,} itens com vetorização...")
    
    all_lines, totais = calcular_legados_item_a_item(nf, matriz)

    return {
        "calculados": totais,
        "linhas": all_lines,
        "etapas": {
            "legados": f"{len(itens)} itens processados",
            "cbs": "CBS/IBS desabilitado" if not usar_cbs_oficial else "N/A"
        }
    }