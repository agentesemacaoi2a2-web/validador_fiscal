# validador_fiscal/agents/supervisor_final_agent.py
"""
Supervisor Final OTIMIZADO
- Gera Excel ao invés de JSON gigante
- Destaca divergências
- Pronto para envio por email
"""

from typing import Dict, Any, List
import time
import os


def run(nf, taxes: Dict[str, Any], resultado: Dict[str, Any], divergencias: List[Dict[str, Any]]) -> Dict[str, Any]:
    """

    # Detectar se é NF única (XML/PDF/IMG sem CSV)  ← LINHA NOVA
    fonte_unica = hasattr(nf, 'chave_acesso') and nf.chave_acesso and len(getattr(nf, 'itens', [])) <= 1
    
    Gera relatório OTIMIZADO com Excel
    
    Args:
        nf: NotaFiscal
        taxes: Impostos calculados
        resultado: Resultado consolidado
        divergencias: Lista de divergências
    
    Returns:
        Dict com relatório + caminho do Excel
    """
    
    print("📊 Supervisor Final: montando relatório executivo...")
    
    # 1. METADATA
    metadata = {
        "chave": getattr(nf, "chave", None),
        "numero": getattr(nf, "numero", None),
        "serie": getattr(nf, "serie", None),
        "data_emissao": getattr(nf, "data_emissao", None),
        "emitente_cnpj": getattr(nf, "emitente_cnpj", None),
        "emitente_nome": getattr(nf, "emitente_nome", None) or "Não informado",
        "destinatario_nome": getattr(nf, "destinatario_nome", None),
        "destinatario_cnpj": getattr(nf, "destinatario_cnpj", None),
        "destinatario_cpf": getattr(nf, "destinatario_cpf", None),
        "total_produtos": resultado.get("total_produtos") or getattr(nf, "total_produtos", None),
        "data_validacao": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # 2. EXTRAIR DADOS CALCULADOS
    calculados = resultado.get("calculados", {}) or taxes.get("calculados", {})
    linhas = resultado.get("linhas", []) or taxes.get("linhas", [])
    
    # 3. CALCULAR TOTAIS
    total_calculado = sum(v for v in calculados.values() if isinstance(v, (int, float)))
    
    # Extrair declarados (simplificado)
    declarados_obj = getattr(nf, "declarados", None)
    total_declarado = 0
    if declarados_obj:
        for imp in ["icms", "pis", "cofins", "ipi", "iss", "irpj", "csll"]:
            val = getattr(declarados_obj, imp, None)
            if val:
                total_declarado += float(val)
    
    divergencia_total = total_calculado - total_declarado
    percentual_divergencia = (divergencia_total / total_declarado * 100) if total_declarado > 0 else 0
    
    # 4. RESUMO EXECUTIVO
    resumo_executivo = {
        "total_itens": len(getattr(nf, "itens", []) or []),
        "total_calculado": round(total_calculado, 2),
        "total_declarado": round(total_declarado, 2),
        "divergencia_absoluta": round(divergencia_total, 2),
        "divergencia_percentual": round(percentual_divergencia, 2),
        "nivel_risco": _calcular_nivel_risco(divergencia_total, percentual_divergencia, total_declarado)
    }
    
    print(f"   Itens: {resumo_executivo['total_itens']:,}")
    print(f"   Calculado: R$ {resumo_executivo['total_calculado']:,.2f}")
    print(f"   Risco: {resumo_executivo['nivel_risco']}")
    
    # 5. TOTAIS POR IMPOSTO
    totais_por_imposto = {}
    for imposto in ["ICMS", "IPI", "PIS", "COFINS", "ISS", "IRPJ", "CSLL"]:
        calc = calculados.get(imposto.lower(), 0.0)
        decl = 0.0
        if declarados_obj:
            decl = float(getattr(declarados_obj, imposto.lower(), 0.0) or 0.0)
        
        if calc > 0 or decl > 0:
            totais_por_imposto[imposto] = {
                "calculado": round(calc, 2),
                "declarado": round(decl, 2),
                "diferenca": round(calc - decl, 2),
                "diferenca_pct": round(((calc - decl) / decl * 100) if decl > 0 else 0, 2)
            }
    
    # 6. DETALHAMENTO ITENS (LIMITADO para não travar)
    itens_detalhados = []  # Pula detalhamento (ganha 5 min!)
    
    print(f"   Itens detalhados: {len(itens_detalhados)}")
    
    # 7. ANÁLISE DE CONFORMIDADE
    analise = _gerar_analise_conformidade(
        resumo_executivo["nivel_risco"],
        divergencias,
        totais_por_imposto
    )

    # Se fonte única, gerar detalhamento campo-a-campo 
    campos_nf = None 

    # Detectar se é fonte única (XML/PDF/IMG)
    fonte_unica = hasattr(nf, 'itens') and len(getattr(nf, 'itens', [])) <= 5
    campos_nf = None
    if fonte_unica:  
        campos_nf = _extrair_campos_nf(nf, totais_por_imposto)  
    
    # 8. MONTAR RELATÓRIO COMPACTO
    relatorio = {
        "metadata": metadata,
        "resumo_executivo": resumo_executivo,
        "totais_por_imposto": totais_por_imposto,
        "itens": itens_detalhados,  # Apenas amostra
        "analise_conformidade": analise,
        "divergencias": divergencias or [],
        "campos_nf": campos_nf, 
        "fonte_unica": fonte_unica, 
        "etapas": resultado.get("etapas", []) or taxes.get("etapas", []),

         # ADICIONAR CAMPOS DIRETOS (para compatibilidade com frontend)
        "chave": getattr(nf, "chave", None),
        "numero": getattr(nf, "numero", None),
        "serie": getattr(nf, "serie", None),
        "data_emissao": getattr(nf, "data_emissao", None),
        "destinatario_nome": getattr(nf, "destinatario_nome", None),
        "destinatario_cnpj": getattr(nf, "destinatario_cnpj", None),
        "destinatario_cpf": getattr(nf, "destinatario_cpf", None),
        
        # ADICIONAR ITENS E DECLARADOS
        "itens": [
            {
                "codigo": getattr(item, "codigo", ""),
                "descricao": getattr(item, "descricao", ""),
                "ncm": getattr(item, "ncm", ""),
                "cfop": getattr(item, "cfop", ""),
                "quantidade": getattr(item, "quantidade", 0),
                "valor_unitario": getattr(item, "valor_unitario", 0),
                "valor_total": getattr(item, "valor_total", 0)
            }
            for item in (getattr(nf, "itens", []) or [])
        ],
        
        "declarados": {
            "icms": getattr(getattr(nf, "declarados", None), "icms", 0) or 0,
            "st": getattr(getattr(nf, "declarados", None), "st", 0) or 0,
            "ipi": getattr(getattr(nf, "declarados", None), "ipi", 0) or 0,
            "pis": getattr(getattr(nf, "declarados", None), "pis", 0) or 0,
            "cofins": getattr(getattr(nf, "declarados", None), "cofins", 0) or 0,
            "iss": getattr(getattr(nf, "declarados", None), "iss", 0) or 0,
            "irpj": getattr(getattr(nf, "declarados", None), "irpj", 0) or 0,
            "csll": getattr(getattr(nf, "declarados", None), "csll", 0) or 0,
        },
        
        # Manter compatibilidade
        "calculados": calculados,
        "linhas": [],  # NÃO salvar 4.9 milhões de linhas!
        
        # ANÁLISE DA IA
        "analise_ia": resultado.get("analise_ia", {})
    }
    
    # 9. GERAR EXCEL
    print("📊 Gerando Excel...")
    try:
        from validador_fiscal.tools.report_generator import gerar_relatorio_excel
        excel_path = gerar_relatorio_excel(relatorio)
        relatorio["excel_path"] = excel_path
        print(f"✅ Excel: {excel_path}")
    except Exception as e:
        print(f"⚠️ Erro ao gerar Excel: {e}")
        relatorio["excel_path"] = None
    
    return relatorio


def _calcular_nivel_risco(divergencia_abs: float, divergencia_pct: float, total_declarado: float = 0) -> str:
    """
    Calcula nível de risco
    Se não tem declarados, retorna N/A
    """
    # Se não tem valores declarados, não pode calcular risco
    if total_declarado == 0:
        return "BAIXO"  # ou "N/A" se preferir
    
    # Com declarados, calcula risco normal
    if abs(divergencia_abs) > 5000 or abs(divergencia_pct) > 15:
        return "ALTO"
    elif abs(divergencia_abs) > 1000 or abs(divergencia_pct) > 5:
        return "MÉDIO"
    else:
        return "BAIXO"


def _gerar_detalhamento_itens_otimizado(nf, linhas: List[Dict], max_itens: int = 1000) -> List[Dict]:
    """
    Gera detalhamento LIMITADO (para não travar)
    Pega primeiros 500 + últimos 500
    """
    
    itens_all = getattr(nf, "itens", []) or []
    total_itens = len(itens_all)
    
    if total_itens == 0:
        return []
    
    # Selecionar amostra
    if total_itens <= max_itens:
        itens_amostra = itens_all
    else:
        metade = max_itens // 2
        itens_amostra = itens_all[:metade] + itens_all[-metade:]
    
    itens_detalhados = []
    
    for idx, item in enumerate(itens_amostra, start=1):
        # Filtrar cálculos deste item
        item_idx_real = itens_all.index(item) + 1 if item in itens_all else idx
        calculos_item = [l for l in linhas if l.get("item_idx") == item_idx_real]
        
        # Organizar por imposto
        impostos_item = {}
        for calc in calculos_item:
            imp = calc.get("imposto", "").upper()
            if imp:
                impostos_item[imp] = {
                    "base": round(calc.get("base", 0), 2),
                    "aliquota_pct": round(calc.get("aliquota", 0) * 100, 4),
                    "valor": round(calc.get("valor", 0), 2),
                    "fonte": calc.get("fonte", "SISTEMA")
                }
        
        item_dict = {
            "numero": item_idx_real,
            "codigo": getattr(item, "codigo", "") or "",
            "descricao": (getattr(item, "descricao", "") or "")[:100],
            "ncm": getattr(item, "ncm", "") or "",
            "cfop": getattr(item, "cfop", "") or "",
            "quantidade": round(getattr(item, "quantidade", 0) or 0, 2),
            "valor_unitario": round(getattr(item, "valor_unitario", 0) or 0, 2),
            "valor_total": round(getattr(item, "valor_total", 0) or 0, 2),
            "impostos": impostos_item
        }
        
        itens_detalhados.append(item_dict)
    
    return itens_detalhados


def _gerar_analise_conformidade(nivel_risco: str, divergencias: List, totais: Dict) -> Dict:
    """Gera análise de conformidade"""
    
    alertas = []
    sugestoes = []
    
    # Alertas baseados em divergências
    if divergencias:
        for div in divergencias[:10]:  # Máx 10 alertas
            if abs(div.get("diferenca", 0)) > 100:
                alertas.append({
                    "tipo": "CRÍTICO" if abs(div.get("diferenca", 0)) > 1000 else "ATENÇÃO",
                    "imposto": div.get("imposto", "").upper(),
                    "mensagem": f"Divergência de R$ {abs(div.get('diferenca', 0)):.2f}"
                })
    
    # Sugestões baseadas no risco
    if nivel_risco == "ALTO":
        sugestoes.append("⚠️ Revisar urgentemente divergências > R$ 1.000")
    elif nivel_risco == "MÉDIO":
        sugestoes.append("⚠️ Revisar divergências > R$ 100")
    else:
        sugestoes.append("✅ Nota fiscal em conformidade")
    
    return {
        "nivel_risco": nivel_risco,
        "alertas": alertas,
        "sugestoes": sugestoes[:5],
        "resumo": _gerar_resumo_conformidade(nivel_risco, len(alertas))
    }


def _gerar_resumo_conformidade(nivel_risco: str, num_alertas: int) -> str:
    """Gera resumo textual"""
    if nivel_risco == "BAIXO":
        return "✅ Nota fiscal em conformidade. Divergências dentro do aceitável."
    elif nivel_risco == "MÉDIO":
        return f"⚠️ Atenção: {num_alertas} alerta(s). Recomenda-se revisão."
    else:
        return f"🚨 Risco alto: {num_alertas} alerta(s) crítico(s). Ação imediata necessária."

def _extrair_campos_nf(nf, totais_impostos: Dict) -> Dict:
    """Extrai todos os campos da NF para exibição detalhada"""
    
    campos = {
        "emitente": {
            "status": "✅",
            "cnpj": getattr(nf, "emitente_cnpj", "N/A"),
            "razao_social": getattr(nf, "emitente_nome", "N/A"),
            "ie": getattr(nf, "emitente_ie", "N/A"),
            "endereco": getattr(nf, "emitente_endereco", "N/A")
        },
        "destinatario": {
            "status": "✅",
            "cnpj": getattr(nf, "destinatario_cnpj", "N/A"),
            "cpf": getattr(nf, "destinatario_cpf", "N/A"),
            "razao_social": getattr(nf, "destinatario_nome", "N/A"),
            "ie": getattr(nf, "destinatario_ie", "N/A")
        },
        "nota": {
            "status": "✅",
            "numero": getattr(nf, "numero", "N/A"),
            "serie": getattr(nf, "serie", "N/A"),
            "chave": getattr(nf, "chave", "N/A"),
            "data_emissao": getattr(nf, "data_emissao", "N/A"),
            "valor_total": getattr(nf, "valor_total", 0.0)
        },
        "impostos": {}
    }
    
    # Comparar impostos declarados vs calculados
    declarados = getattr(nf, "declarados", None)
    
    for imp_nome, dados in totais_impostos.items():
        calc = dados.get("calculado", 0)
        decl = dados.get("declarado", 0)
        
        diff = abs(calc - decl)
        status = "✅" if diff < 10 else ("⚠️" if diff < 100 else "❌")
        
        campos["impostos"][imp_nome] = {
            "status": status,
            "declarado": f"R$ {decl:,.2f}",
            "calculado": f"R$ {calc:,.2f}",
            "diferenca": f"R$ {diff:,.2f}" if diff > 0 else "✅ CORRETO"
        }
    
    return campos