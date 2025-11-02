# validador_fiscal/app/app_completa_melhorada.py
"""	
╔══════════════════════════════════════════════════════════════════════════════╗
║                    VALIDADOR FISCAL NFS - PROFISSIONAL                       ║
║                       Sistema Multi-Agente Inteligente                       ║
╚══════════════════════════════════════════════════════════════════════════════╝

📋 DESCRIÇÃO:
    Sistema completo de validação e cálculo de impostos para Notas Fiscais
    de Serviço (NFS-e) e Produtos (NF-e), com detecção automática de 
    divergências e geração de relatórios detalhados.

🎯 FUNCIONALIDADES PRINCIPAIS:
    • Leitura inteligente de múltiplos formatos (CSV, XML, PDF, Imagens)
    • Cálculo automático de impostos legados e reforma tributária
    • Detecção de divergências entre declarado vs calculado
    • Chat fiscal com RAG para consultas tributárias
    • Geração de relatórios em Excel/JSON
    • Interface web responsiva com Streamlit

💰 IMPOSTOS SUPORTADOS:
    Legados:    ICMS, ST, DIFAL, IPI, PIS, COFINS, ISS, IRPJ, CSLL
    Reforma:    CBS, IBS, IS (Imposto Seletivo)

🏗️ ARQUITETURA:
    Multi-Agente com orquestração via CrewAI:
    1. Leitor      → Ingere documentos (CSV/XML/PDF/IMG)
    2. Matriz      → Busca alíquotas (CFOP/NCM/CST)
    3. Legados     → Calcula impostos tradicionais
    4. Reforma     → Calcula CBS/IBS/IS via API
    5. Consolidador→ Integra resultados
    6. Divergências→ Detecta inconsistências
    7. Supervisor  → Gera relatório final

📊 FLUXOS DE USO:
    A) CSV Completo (Cabeçalho + Itens):
       → Validação massiva com milhares de itens
       → Gera resumo executivo + análise detalhada
    
    B) XML/PDF/Imagem (NF única):
       → Extração + validação campo a campo
       → Exibe detalhamento completo da nota

🔧 TECNOLOGIAS:
    • Streamlit (UI)
    • CrewAI (Orquestração Multi-Agente)
    • Pandas (Processamento de dados)
    • Plotly (Visualizações)
    • Anthropic Claude (RAG e Chat)

👤 AUTOR: Suzy Pedrosa
📅 VERSÃO: 3.0 Final
📝 ÚLTIMA ATUALIZAÇÃO: Outubro 2025
"""

import os, sys, io, json, time, threading
from typing import Optional, List, Dict

# Bootstrap paths
APP_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(APP_DIR, ".."))
PARENT = os.path.abspath(os.path.join(ROOT, ".."))
for p in (PARENT, ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

# Imports
from dotenv import load_dotenv
load_dotenv()
from openai import OpenAI

# Inicializar cliente OpenAI
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Core
from validador_fiscal.agents.supervisor_agent import run_pipeline

# Memory + RAG + News
from validador_fiscal.memory.store import (
    save_chat_message as file_save_msg,
    load_chat_history as file_load_hist,
)
from validador_fiscal.tools.rag_tool import rag_query
from validador_fiscal.tools.news_tool import get_news

# DB
from validador_fiscal.db.base import Base, engine, SessionLocal
from validador_fiscal.db.crud import save_nf_full, save_nf_csv_auto

# Config
st.set_page_config(
    page_title="Validador Fiscal NFS - Profissional",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Melhorado
st.markdown("""
<style>
    /* Remover espaço do topo */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }
    
    .main .block-container {
        max-width: 100%;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    
    /* Header principal */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    
    /* Cards de agentes */
    .agent-strip {
        display: flex;
        gap: 12px;
        overflow-x: auto;
        padding: 12px 0;
        margin-bottom: 20px;
    }
    
    .agent-card {
        min-width: 140px;
        padding: 16px;
        border-radius: 12px;
        background: white;
        border: 2px solid #e7e7e9;
        text-align: center;
        transition: all 0.3s;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    
    .agent-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 20px rgba(102, 126, 234, 0.2);
        border-color: #667eea;
    }
    
    .agent-card .icon {
        font-size: 2.5rem;
        margin-bottom: 8px;
    }
    
    .agent-card .title {
        font-weight: 700;
        font-size: 1rem;
        color: #333;
        margin-bottom: 4px;
    }
    
    .agent-card .desc {
        font-size: 0.75rem;
        color: #666;
        line-height: 1.3;
    }
    
    /* Métricas */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
        margin-bottom: 1rem;
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        color: #667eea;
        margin-bottom: 0.5rem;
    }
    
    .metric-label {
        font-size: 0.9rem;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Badges de risco */
    .risk-badge {
        display: inline-block;
        padding: 8px 16px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .risk-baixo { background: #10b981; color: white; }
    .risk-medio { background: #f59e0b; color: white; }
    .risk-alto { background: #ef4444; color: white; }
    
    /* Botões */
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
        font-weight: 600;
        padding: 0.75rem 1.5rem;
        border-radius: 10px;
        border: none;
        transition: all 0.3s;
        box-shadow: 0 4px 10px rgba(102, 126, 234, 0.3);
    }

    /* Botão download JSON verde */
    div[data-testid="stDownloadButton"] button {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
        color: white !important;
    }

    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 15px rgba(102, 126, 234, 0.4);
    }

    /* Botão primário (downloads) */
    .stButton>button[kind="primary"] {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
    }

    /* Botão secundário */
    .stButton>button[kind="secondary"] {
        background: linear-gradient(135deg, #6b7280 0%, #4b5563 100%) !important;
    }

    /* Botão download desabilitado */
    .stDownloadButton>button:disabled {
        background: #e5e7eb !important;
        color: #9ca3af !important;
        cursor: not-allowed !important;
    }
    
    /* Chat */
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    
    .chat-user {
        background: #f0f7ff;
        border-left: 4px solid #667eea;
    }
    
    .chat-assistant {
        background: #f9fafb;
        border-left: 4px solid #10b981;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px 10px 0 0;
        padding: 12px 24px;
        font-weight: 600;
    }
    
    /* Progress */
    .stProgress > div > div {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* News cards */
    .news-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 4px solid #667eea;
        margin-bottom: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    
    .news-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #333;
        margin-bottom: 0.5rem;
    }
    
    .news-meta {
        font-size: 0.85rem;
        color: #666;
        margin-bottom: 0.75rem;
    }
</style>
"""

, unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>📊 Validador Fiscal NFS - Profissional</h1>
    <p>Sistema Inteligente Multi-Agente com RAG, Chat e Histórico Completo</p>
</div>
""", unsafe_allow_html=True)

st.markdown("---")


# ==================== FUNÇÕES AUXILIARES ====================

TAX_MAP = {
    "pis": "pis", "cofins": "cofins", "ipi": "ipi", "icms": "icms", "st": "st",
    "difal": "difal", "iss": "iss", "irpj": "irpj", "csll": "csll",
    "cbs": "cbs", "ibs": "ibs", "is": "is_"
}

def _load_active_report() -> Optional[dict]:
    path = st.session_state.get("rel_json")
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def _summarize_report(rel: dict) -> str:
    if not rel:
        return "(sem relatório ativo)"
    calc = rel.get("calculados", {})
    lines = ["📊 **Totais calculados:**\n"]
    for k in ["icms","st","difal","ipi","pis","cofins","iss","irpj","csll"]:
        if k in calc:
            try:
                lines.append(f"- **{k.upper()}:** R$ {float(calc[k]):,.2f}")
            except:
                pass
    return "\n".join(lines)

def _answer_from_report(question: str, rel: dict) -> str:
    if not rel:
        return "❌ Não há relatório ativo. Valide uma NF primeiro na aba 'Validador de NF'."
    
    q = question.lower()
    calc = rel.get("calculados", {})
    resumo = rel.get("resumo_executivo", {})
    divergencias = rel.get("divergencias", [])
    
    # Perguntas sobre divergências
    if any(palavra in q for palavra in ["divergência", "divergencias", "inconsistência", "erro", "problema"]):
        total_decl = resumo.get("total_declarado", 0)
        
        if total_decl == 0:
            return "✅ **Não é possível calcular divergências** porque o CSV não contém os valores declarados dos impostos.\n\n📊 **Totais calculados:**\n" + _summarize_report(rel)
        
        diverg_abs = resumo.get("divergencia_absoluta", 0)
        diverg_pct = resumo.get("divergencia_percentual", 0)
        
        if abs(diverg_abs) < 100:
            return f"✅ **Nenhuma divergência significativa encontrada!**\n\n📊 Divergência total: R$ {abs(diverg_abs):,.2f} ({diverg_pct:+.2f}%)\n\n✨ Os valores calculados estão de acordo com os declarados."
        else:
            return f"⚠️ **Divergências encontradas:**\n\n💰 Total: R$ {abs(diverg_abs):,.2f} ({diverg_pct:+.2f}%)\n📊 {len(divergencias)} item(ns) com diferenças\n\n" + _summarize_report(rel)
    
    # Buscar impostos mencionados
    hits = []
    for key, model_key in TAX_MAP.items():
        if key in q and model_key in calc and calc[model_key] is not None:
            try:
                hits.append(f"**{model_key.upper()}:** R$ {float(calc[model_key]):,.2f}")
            except:
                pass
    
    if hits:
        return "📊 **Valores encontrados:**\n\n" + "\n".join(hits)
    else:
        return _summarize_report(rel)

# ==================== TABS ====================

def _exibir_nf_detalhada(campos: Dict):
    """Exibe NF campo a campo"""
    
    # Carregar relatório completo
    rel = _load_active_report() or {}
    
    st.markdown("### 📄 Detalhamento da Nota Fiscal")
    
    # Emitente
    with st.expander("🏢 **EMITENTE**", expanded=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**Razão Social:** {campos['emitente']['razao_social']}")
            st.markdown(f"**CNPJ:** {campos['emitente']['cnpj']}")
            st.markdown(f"**IE:** {campos['emitente']['ie']}")
        with col2:
            st.markdown(f"**Status:** {campos['emitente']['status']}")
    
    # Destinatário
    with st.expander("👤 **DESTINATÁRIO**", expanded=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            dest_nome = rel.get('destinatario_nome') or 'N/A'
            dest_cpf = rel.get('destinatario_cpf') or campos['destinatario'].get('cpf', None)
            dest_cnpj = rel.get('destinatario_cnpj') or campos['destinatario'].get('cnpj', None)
        
            st.markdown(f"**Razão Social:** {dest_nome}")
        
            # Mostrar CPF ou CNPJ
            if dest_cpf:
                st.markdown(f"**CPF:** {dest_cpf}")
            elif dest_cnpj:
                st.markdown(f"**CNPJ:** {dest_cnpj}")
            else:
                st.markdown(f"**CPF/CNPJ:** None")
        with col2:
            st.markdown(f"**Status:** {campos['destinatario']['status']}")
    
    # Nota
    with st.expander("📋 **DADOS DA NOTA**", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Número", rel.get('numero') or campos['nota'].get('numero', 'N/A'))
            st.metric("Série", rel.get('serie') or campos['nota'].get('serie', 'N/A'))
        with col2:
            st.metric("Data Emissão", rel.get('data_emissao') or campos['nota'].get('data_emissao', 'N/A'))
            itens = rel.get("itens", [])
            if itens and len(itens) > 0:
                # Pegar total_produtos do relatório (vem do XML com desconto aplicado)
                total_itens = rel.get("metadata", {}).get("total_produtos") or sum(item.get("valor_total", 0) for item in itens)
                st.metric("Valor Total", f"R$ {total_itens:,.2f}")
            else:
                st.metric("Valor Total", "R$ 0.00")
        with col3:
            st.markdown(f"**Status:** {campos['nota']['status']}")
        
        if itens and len(itens) > 0:
            st.markdown(f"#### 📦 Itens ({len(itens)})")
            for idx, item in enumerate(itens, 1):
                    st.markdown(f"""**Item {idx}:** {item.get('descricao', 'Produto/Serviço')}  
- **Código:** {item.get('codigo', 'N/A')} | **NCM:** {item.get('ncm', 'N/A')} | **CFOP:** {item.get('cfop', 'N/A')}
- **Qtd:** {item.get('quantidade', 0):,.2f} | **Unit:** R$ {item.get('valor_unitario', 0):,.2f} | **Total:** R$ {item.get('valor_total', 0):,.2f}""")
                    if idx < len(itens):
                        st.markdown("---")
        else:
            st.warning("⚠️ Nenhum item encontrado")

    # Impostos
    st.markdown("### 💰 Impostos - Declarado vs Calculado")
    declarados_raw = rel.get('declarados', {})

    # DEBUG
    print(f"🔍 APP - Declarados lidos do JSON: {declarados_raw}")
    
    for imp, dados in campos['impostos'].items():
        imp_declarado = declarados_raw.get(imp.lower(), 0)
        with st.expander(f"{dados['status']} **{imp.upper()}**"):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Declarado", f"R$ {imp_declarado:,.2f}")
            with col2:
                st.metric("Calculado", dados['calculado'])
            with col3:
                st.metric("Diferença", dados['diferenca'])
            with col4:
                st.markdown(f"**Status:** {dados['status']}")


def _exibir_resumo_executivo(relatorio: dict):
    """Exibe resumo executivo COMPLETO com gráficos (CSV)"""
    resumo = relatorio.get("resumo_executivo", {})
    totais = relatorio.get("totais_por_imposto", {})
    
    # ==================== CABEÇALHO ====================
    st.markdown("### 📊 Resumo Executivo")
    
    # Cards principais
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📦 Itens Processados", f"{resumo.get('total_itens', 0):,}")
    with col2:
        st.metric("💰 Total Calculado", f"R$ {resumo.get('total_calculado', 0):,.2f}")
    with col3:
        if resumo.get('total_declarado', 0) > 0:
            diverg = abs(resumo.get('divergencia_absoluta', 0))
            st.metric("⚖️ Divergência Total", f"R$ {diverg:,.2f}")
        else:
            st.metric("⚖️ Divergência", "N/A")
    with col4:
        risco = resumo.get('nivel_risco', 'BAIXO')
        cor_map = {'BAIXO': '🟢', 'MÉDIO': '🟡', 'ALTO': '🔴'}
        st.metric("🎯 Nível de Risco", f"{cor_map.get(risco, '⚪')} {risco}")
    
    st.markdown("---")
    
    # ==================== GRÁFICOS ====================
    
    # Preparar dados para gráficos
    impostos_data = []
    for imp, valores in totais.items():
        calc = valores.get("calculado", 0)
        decl = valores.get("declarado", 0)
        if calc > 0 or decl > 0:
            impostos_data.append({
                "Imposto": imp.upper(),
                "Calculado": calc,
                "Declarado": decl,
                "Diferença": abs(calc - decl)
            })
    
    if impostos_data:
        df_impostos = pd.DataFrame(impostos_data)
        
        # 2 colunas para gráficos
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            st.markdown("#### 📊 Impostos Calculados vs Declarados")
            
            # Gráfico de barras agrupadas
            fig_barras = go.Figure()
            
            fig_barras.add_trace(go.Bar(
                name='Calculado',
                x=df_impostos['Imposto'],
                y=df_impostos['Calculado'],
                marker_color='#1f77b4',
                text=df_impostos['Calculado'].apply(lambda x: f'R$ {x:,.2f}'),
                textposition='outside'
            ))
            
            fig_barras.add_trace(go.Bar(
                name='Declarado',
                x=df_impostos['Imposto'],
                y=df_impostos['Declarado'],
                marker_color='#ff7f0e',
                text=df_impostos['Declarado'].apply(lambda x: f'R$ {x:,.2f}'),
                textposition='outside'
            ))
            
            fig_barras.update_layout(
                barmode='group',
                height=400,
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                yaxis_title="Valor (R$)",
                xaxis_title="Impostos"
            )
            
            st.plotly_chart(fig_barras, use_container_width=True)
        
        with col_g2:
            st.markdown("#### 🎯 Distribuição dos Impostos Calculados")
            
            # Gráfico de pizza
            df_pizza = df_impostos[df_impostos['Calculado'] > 0].copy()
            
            if not df_pizza.empty:
                fig_pizza = px.pie(
                    df_pizza,
                    values='Calculado',
                    names='Imposto',
                    title="",
                    hole=0.4,  # Donut chart
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                
                fig_pizza.update_traces(
                    textposition='inside',
                    textinfo='label+percent',
                    hovertemplate='<b>%{label}</b><br>R$ %{value:,.2f}<br>%{percent}<extra></extra>'
                )
                
                fig_pizza.update_layout(height=400)
                
                st.plotly_chart(fig_pizza, use_container_width=True)
            else:
                st.info("Nenhum imposto calculado para exibir no gráfico de pizza")
        
        # Gráfico de divergências (largura total)
        st.markdown("#### ⚠️ Análise de Divergências")
        
        df_diverg = df_impostos[df_impostos['Diferença'] > 0].copy()
        
        if not df_diverg.empty:
            fig_diverg = px.bar(
                df_diverg.sort_values('Diferença', ascending=False),
                x='Imposto',
                y='Diferença',
                title="",
                color='Diferença',
                color_continuous_scale='Reds',
                text='Diferença'
            )
            
            fig_diverg.update_traces(
                texttemplate='R$ %{text:,.2f}',
                textposition='outside'
            )
            
            fig_diverg.update_layout(
                height=350,
                showlegend=False,
                coloraxis_showscale=False,
                yaxis_title="Divergência (R$)",
                xaxis_title="Impostos"
            )
            
            st.plotly_chart(fig_diverg, use_container_width=True)
        else:
            st.success("✅ Nenhuma divergência detectada! Todos os impostos estão corretos.")
    
    else:
        st.info("ℹ️ Nenhum dado de impostos disponível para exibir gráficos")
    
    # ==================== TABELA DETALHADA ====================
    st.markdown("---")
    st.markdown("#### 📋 Detalhamento por Imposto")
    
    if impostos_data:
        df_tabela = pd.DataFrame(impostos_data)
        
        # Adicionar coluna de status
        df_tabela['Status'] = df_tabela.apply(
            lambda row: '✅ OK' if row['Diferença'] < 0.01 else '⚠️ Divergência',
            axis=1
        )
        
        # Formatar valores monetários
        for col in ['Calculado', 'Declarado', 'Diferença']:
            df_tabela[col] = df_tabela[col].apply(lambda x: f"R$ {x:,.2f}")
        
        st.dataframe(
            df_tabela[['Imposto', 'Calculado', 'Declarado', 'Diferença', 'Status']],
            use_container_width=True,
            hide_index=True
        )
    
    else:
        st.info("ℹ️ Nenhum dado disponível para exibir na tabela")

aba_val, aba_chat, aba_news = st.tabs([
    "📊 Validador de NF",
    "💬 Chat Fiscal",
    "📰 Notícias e Dicas"
])

# ==================== ABA 1: VALIDADOR ====================

with aba_val:
    # Verificar se há resultado para mostrar
    if st.session_state.get('mostrar_resultado') and st.session_state.get('ultimo_relatorio'):
        relatorio = st.session_state['ultimo_relatorio']
        
        # Mostrar resultado salvo
        resumo = relatorio.get("resumo_executivo", {})
        totais = relatorio.get("totais_por_imposto", {})
        
        st.success("✅ **Última validação concluída!**")
        
        # [COPIAR TODA A SEÇÃO DE EXIBIÇÃO DE RESULTADOS AQUI]
        # (métricas, gráficos, downloads)
    
    # Cards dos agentes
    st.markdown("""
    <div class="agent-strip">
        <div class="agent-card">
            <div class="icon">🧠</div>
            <div class="title">Leitor</div>
            <div class="desc">CSV/XML/PDF/Imagem</div>
        </div>
        <div class="agent-card">
            <div class="icon">🗺️</div>
            <div class="title">Matriz</div>
            <div class="desc">CFOP/NCM/CST</div>
        </div>
        <div class="agent-card">
            <div class="icon">🏭</div>
            <div class="title">Legados</div>
            <div class="desc">ICMS, PIS, COFINS<br>IPI, ISS, IRPJ, CSLL</div>
        </div>
        <div class="agent-card">
            <div class="icon">🏛️</div>
            <div class="title">CBS/IBS/IS</div>
            <div class="desc">Reforma Tributária</div>
        </div>
        <div class="agent-card">
            <div class="icon">📌</div>
            <div class="title">Consolidador</div>
            <div class="desc">Integração</div>
        </div>
        <div class="agent-card">
            <div class="icon">🚨</div>
            <div class="title">Divergências</div>
            <div class="desc">Auditoria</div>
        </div>
        <div class="agent-card">
            <div class="icon">🧑‍⚖️</div>
            <div class="title">Supervisor</div>
            <div class="desc">Revisão Final</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.subheader("📂 Upload de Documentos")

    # Funções de validação
    import re, csv, zipfile
    from io import BytesIO

    def _read_header_first_row_LIGHT(uploaded_file):
        """Lê APENAS primeiras linhas (não trava!)"""
        uploaded_file.seek(0)
        sample = uploaded_file.read(50000).decode('utf-8', errors='ignore')
        uploaded_file.seek(0)
    
        lines = sample.splitlines()[:100]
        if len(lines) < 2:
            return [], None
    
        first_line = lines[0]
        sep = ';' if first_line.count(';') > first_line.count(',') else ','
    
        header = [c.strip() for c in lines[0].split(sep)]
        first = [c.strip() for c in lines[1].split(sep)]
        return header, first

    def _extract_key_LIGHT(uploaded_file):
        """Extrai chave SEM carregar arquivo inteiro"""
        uploaded_file.seek(0)
        name = uploaded_file.name.lower()
    
        if name.endswith(".zip"):
            try:
                raw = uploaded_file.read()
                uploaded_file.seek(0)
                with zipfile.ZipFile(BytesIO(raw), "r") as z:
                    csvs = [n for n in z.namelist() if n.lower().endswith(".csv")]
                    chosen = next((n for n in csvs if "item" in n.lower()), csvs[0]) if csvs else None
                    if not chosen:
                        return None
                    data = z.read(chosen)
                    sample = data[:50000].decode('utf-8', errors='ignore')
                    lines = sample.splitlines()[:100]
                    if len(lines) < 2:
                        return None
                    sep = ';' if lines[0].count(';') > lines[0].count(',') else ','
                    header = lines[0].split(sep)
                    first = lines[1].split(sep)
            except:
                return None
        else:
            header, first = _read_header_first_row_LIGHT(uploaded_file)
    
        if not header or not first:
            return None
    
        patterns = ("chave", "acesso", "chavenfe", "chnfe")
        for idx, col in enumerate(header):
            if any(p in col.lower() for p in patterns):
                if idx < len(first):
                    digits = "".join(re.findall(r"\d", first[idx]))
                    if len(digits) >= 30:
                        return digits
        return None

    # Uploads
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        up_csv_list = st.file_uploader("CSV (Cabeçalho + Itens)", type=["csv"], accept_multiple_files=True, key="up_csv")
                    
    with col2:
        up_xml = st.file_uploader("XML (NF-e)", type=["xml"], key="up_xml")
        
    with col3:
        up_pdf = st.file_uploader("PDF", type=["pdf"], key="up_pdf")
        
    with col4:
        up_img = st.file_uploader("Imagem", type=["png","jpg","jpeg"], key="up_img")
        
    # Validar chaves
    chaves = set()
    if up_csv_list and len(up_csv_list) >= 2:
        for f in up_csv_list:
            k = _extract_key_LIGHT(f)
            if k:
                chaves.add(k)

    # Habilitar botão
    botao_habilitado = (len(chaves) == 1 and len(up_csv_list) >= 2) or up_xml or up_pdf or up_img

    usar_cbs = st.checkbox("✅ Usar API CBS/IBS/IS (Reforma)", value=False)

    # Botão validar
    if st.button("🚀 VALIDAR AGORA", use_container_width=True, disabled=not botao_habilitado):
        # Salvar temporariamente
        temp_paths = []
        temp_xml = None
        temp_pdf = None
        temp_img = None
    
        os.makedirs("data/uploads", exist_ok=True)
     
        # Salvar CSVs
        if up_csv_list:
            for f in up_csv_list:
                temp = os.path.join("data/uploads", f.name)
                with open(temp, "wb") as out:
                    out.write(f.read())
                temp_paths.append(temp)
    
        # Salvar XML
        if up_xml:
            temp_xml = os.path.join("data/uploads", up_xml.name)
            with open(temp_xml, "wb") as out:
                out.write(up_xml.read())
    
        # Salvar PDF
        if up_pdf:
            temp_pdf = os.path.join("data/uploads", up_pdf.name)
            with open(temp_pdf, "wb") as out:
                out.write(up_pdf.read())
    
        # Salvar Imagem
        if up_img:
            temp_img = os.path.join("data/uploads", up_img.name)
            with open(temp_img, "wb") as out:
                out.write(up_img.read())
    
        if temp_paths or temp_xml or temp_pdf or temp_img:
            # Estimar tempo
            if temp_paths and len(temp_paths) >= 2:
                tempo_estimado = "5-10 min para arquivos grandes"
            else:
                tempo_estimado = "30-90s"
        
            with st.spinner(f"⏳ Processando... Aguarde ({tempo_estimado})"):
                try:
                    docs = {
                        "nf_csv_file": temp_paths if temp_paths else None,
                        "xml_file": temp_xml,
                        "pdf_file": temp_pdf,
                        "image_file": temp_img
                     }
                
                    rel_path = run_pipeline(
                        docs=docs,
                        usar_cbs_oficial=usar_cbs,
                        progress_path="data/progress.jsonl"
                    )
                
                    st.session_state["rel_json"] = rel_path
                
                    # Carregar relatório
                    with open(rel_path, 'r', encoding='utf-8') as f:
                        relatorio = json.load(f)
                
                    st.success("✅ **Validação concluída!**")

                    # MODO DETALHADO (XML/PDF/IMG)
                    if relatorio.get("fonte_unica") and relatorio.get("campos_nf"):
                        _exibir_nf_detalhada(relatorio["campos_nf"])
                    else:
                        # MODO RESUMO (CSV)
                        _exibir_resumo_executivo(relatorio)
                
                    # Download
                    # Salvar relatório no session_state para manter após download
                    st.session_state['ultimo_relatorio'] = relatorio
                    st.session_state['mostrar_resultado'] = True
                    
                    # Download
                    # ANÁLISE DA IA (se disponível)
                    analise_ia = relatorio.get("analise_ia", {})
                    
                    if analise_ia and analise_ia.get("metodo") == "ia_completa":
                        st.markdown("---")
                        st.markdown("### 🤖 Análise da Inteligência Artificial")
                        
                        # Badges
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            regime = analise_ia.get('regime_tributario', 'N/A').replace('_', ' ').title()
                            st.metric("📋 Regime", regime)
                        with col2:
                            tipo = analise_ia.get('tipo_operacao', 'N/A').replace('_', ' ').title()
                            st.metric("📦 Operação", tipo)
                        with col3:
                            conf = analise_ia.get('confianca', 0) * 100
                            st.metric("✅ Confiança", f"{conf:.0f}%")
                        
                        # Particularidades
                        part = analise_ia.get('particularidades', [])
                        if part:
                            st.markdown("**📌 Particularidades:**")
                            for p in part:
                                st.info(f"• {p}")
                        
                        # Validação por imposto
                        validacao = analise_ia.get('validacao', {})
                        if validacao:
                            st.markdown("**💬 Comentários da IA por Imposto:**")
                            
                            for imp_key, val in validacao.items():
                                status = val.get('status', '')
                                motivo = val.get('motivo', '')
                                
                                if status == "correto":
                                    st.success(f"**{imp_key.upper()}:** ✅ {motivo}")
                                elif status == "divergente":
                                    st.error(f"**{imp_key.upper()}:** ❌ {motivo}")
                                else:
                                    st.warning(f"**{imp_key.upper()}:** ⚠️ {motivo}")
                        
                        # Alertas
                        alertas = analise_ia.get('alertas_criticos', [])
                        if alertas:
                            st.markdown("**🚨 Alertas Críticos:**")
                            for a in alertas:
                                st.error(f"⚠️ {a}")
                        
                        # Recomendações
                        rec = analise_ia.get('recomendacoes', [])
                        if rec:
                            st.markdown("**💡 Recomendações:**")
                            for r in rec:
                                st.success(f"✅ {r}")
                    
                    st.markdown("### 📥 Downloads e Ações")
                                     
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        json_str = json.dumps(relatorio, ensure_ascii=False, indent=2)
                        st.download_button(
                            "📄 Baixar JSON",
                            json_str,
                            f"relatorio_{int(time.time())}.json",
                            "application/json",
                            use_container_width=True,
                            type="primary"
                        )
                    
                    with col2:
                        excel_path = relatorio.get('excel_path')
                        if excel_path and os.path.exists(excel_path):
                            with open(excel_path, 'rb') as f:
                                st.download_button(
                                    "📊 Baixar Excel",
                                    f.read(),
                                    os.path.basename(excel_path),
                                    "application/vnd.ms-excel",
                                    use_container_width=True,
                                    type="primary"
                                )
                        else:
                            st.button(
                                "📊 Baixar Excel",
                                disabled=True,
                                use_container_width=True,
                                type="primary",
                                help="Instale 'openpyxl' para gerar Excel"
                            )

                    with col3:
                        if st.button("🗑️ Nova Validação", use_container_width=True, type="secondary"):
                            st.session_state['mostrar_resultado'] = False
                            st.session_state['ultimo_relatorio'] = None
                            st.session_state['rel_json'] = None
                            st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Erro: {e}")
                    st.exception(e)
        else:
            st.warning("⚠️ Faça upload de pelo menos um arquivo!")

# ==================== GRÁFICOS INTELIGENTES ====================

def detectar_tipo_grafico(pergunta: str) -> str:
    p = pergunta.lower()
    if any(palavra in p for palavra in ["pizza", "torta", "percentual"]):
        return "pizza"
    if any(palavra in p for palavra in ["comparar", "comparativo", "vs"]):
        return "comparativo"
    if any(palavra in p for palavra in ["top", "maior", "ranking"]):
        return "ranking"
    return "barras"

def gerar_grafico_inteligente(tipo: str, dados: dict, pergunta: str = ""):
    df = pd.DataFrame([
        {"Imposto": imp.upper(), "Calculado": d.get("calculado", 0)}
        for imp, d in dados.items()
        if d.get("calculado", 0) > 0
    ]).sort_values("Calculado", ascending=False)
    
    if df.empty:
        return None
    
    if tipo == "barras":
        fig = px.bar(df, x='Calculado', y='Imposto', orientation='h', title="📊 Impostos Calculados", color='Calculado', color_continuous_scale='Blues', text='Calculado')
        fig.update_traces(texttemplate='R$ %{x:,.0f}', textposition='outside', hovertemplate='<b>%{y}</b><br>Valor: R$ %{x:,.2f}<extra></extra>')
        fig.update_layout(height=450, showlegend=False, coloraxis_showscale=False, template='plotly_white', margin=dict(l=100, r=50, t=50, b=50))
        return fig
    
    elif tipo == "pizza":
        fig = px.pie(df, values='Calculado', names='Imposto', title="🥧 Distribuição de Impostos", color_discrete_sequence=px.colors.sequential.Blues[::-1])
        fig.update_traces(textinfo='percent+label', hovertemplate='<b>%{label}</b><br>Valor: R$ %{value:,.2f}<br>Percentual: %{percent}<extra></extra>')
        fig.update_layout(height=450, template='plotly_white', margin=dict(l=50, r=50, t=50, b=50))
        return fig
    
    elif tipo == "comparativo":
        fig = go.Figure()
        fig.add_trace(go.Bar(name='Calculado', x=df['Imposto'], y=df['Calculado'], marker_color='#4A90E2', text=['R$ {:.2f}'.format(x) for x in df['Calculado']], textposition='outside', hovertemplate='<b>%{x}</b><br>Valor: R$ %{y:,.2f}<extra></extra>'))
        fig.update_layout(title="⚖️ Comparativo de Impostos", height=450, template='plotly_white', margin=dict(l=100, r=50, t=50, b=50), yaxis_title="Valor (R$)")
        return fig
    
    return None
def processar_pergunta_grafico(pergunta: str, relatorio: dict):
    palavras_grafico = ["gráfico", "grafico", "mostre", "pizza", "comparativo", "top"]
    if any(palavra in pergunta.lower() for palavra in palavras_grafico):
        tipo = detectar_tipo_grafico(pergunta)
        dados = relatorio.get("totais_por_imposto", {}) if relatorio else {}
        if dados:
            return {"gerar_grafico": True, "tipo": tipo, "dados": dados}
    return {"gerar_grafico": False}

with aba_chat:
    # ========================================
    # CARDS DE FUNCIONALIDADES DO CHAT
    # ========================================
    
    st.markdown("""
    <style>
    .func-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px;
        padding: 20px;
        color: white;
        margin: 8px 0;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        transition: transform 0.2s;
    }
    .func-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 16px rgba(0,0,0,0.2);
    }
    .func-icon {
        font-size: 40px;
        margin-bottom: 10px;
    }
    .func-title {
        font-size: 16px;
        font-weight: 600;
        margin-bottom: 5px;
    }
    .func-desc {
        font-size: 12px;
        opacity: 0.9;
        line-height: 1.4;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("### 💡 O que posso fazer por você?")
    
    # Grid de 3 colunas
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="func-card">
            <div class="func-icon">📊</div>
            <div class="func-title">Analisar Documentos</div>
            <div class="func-desc">Extrair dados de NF, calcular impostos e gerar relatórios detalhados</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="func-card">
            <div class="func-icon">📈</div>
            <div class="func-title">Criar Gráficos</div>
            <div class="func-desc">Gerar gráficos de barras, pizza e comparativos interativos</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="func-card">
            <div class="func-icon">🔍</div>
            <div class="func-title">Consultar Sites</div>
            <div class="func-desc">Buscar alíquotas atualizadas em portais oficiais (SEFAZ, Receita)</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="func-card">
            <div class="func-icon">📋</div>
            <div class="func-title">Explicar Conceitos</div>
            <div class="func-desc">Explicar ST, DIFAL, MVA e outros impostos de forma didática</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="func-card">
            <div class="func-icon">💾</div>
            <div class="func-title">Exportar Dados</div>
            <div class="func-desc">Gerar Excel, CSV, PDF com relatórios completos</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="func-card">
            <div class="func-icon">🌐</div>
            <div class="func-title">Pesquisar Legislação</div>
            <div class="func-desc">Buscar mudanças recentes e links para sites oficiais</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Exemplos de perguntas
    st.markdown("### 💬 Exemplos de Perguntas:")
    
    col_ex1, col_ex2 = st.columns(2)
    
    with col_ex1:
        st.markdown("""
        **📊 Sobre Documentos:**
        - "Analise essa nota fiscal"
        - "Calcule todos os impostos"
        - "Mostre gráfico dos valores"
        - "Quais as divergências?"
        
        **🔍 Consultas Web:**
        - "Qual alíquota de ISS em São Paulo?"
        - "Site oficial da SEFAZ RJ"
        - "Mudanças no ICMS 2025"
        - "Tabela MVA para eletrônicos"
        """)
    
    with col_ex2:
        st.markdown("""
        **📈 Análises e Gráficos:**
        - "Crie gráfico de barras dos impostos"
        - "Compare calculado vs declarado"
        - "Mostre carga tributária total"
        - "Top 10 itens com divergências"
        
        **📋 Explicações:**
        - "O que é substituição tributária?"
        - "Como calcular DIFAL?"
        - "Explique reforma tributária 2026"
        - "Diferença entre PIS cumulativo e não-cumulativo"
        """)
    
    st.markdown("---")

    st.subheader("💬 Chat Fiscal Inteligente")
    st.caption("Pergunte sobre o relatório ativo ou consulte a base de conhecimento")
    
    # Verificar se há relatório ativo
    if not st.session_state.get("rel_json"):
        st.info("💡 **Dica:** Valide uma NF na aba 'Validador de NF' primeiro, depois volte aqui para fazer perguntas sobre o relatório!")
    
    # Inicializar msgs vazio
    if "msgs" not in st.session_state:
        st.session_state["msgs"] = []
    
    # Exibir histórico
    for msg in st.session_state["msgs"]:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        
        if role == "user":
            st.markdown(f'<div class="chat-message chat-user">👤 **Você:** {content}</div>', unsafe_allow_html=True)
        elif role == "assistant":
            st.markdown(f'<div class="chat-message chat-assistant">🤖 **Assistente:** {content}</div>', unsafe_allow_html=True)
        elif role == "chart":
            # Renderizar gráfico
            tipo = msg.get("tipo")
            dados = msg.get("dados", {})
            
            if dados:
                df_chat = pd.DataFrame([
                    {"Imposto": imp, "Valor": d.get("calculado", 0)}
                    for imp, d in dados.items()
                    if d.get("calculado", 0) > 0
                ]).sort_values("Valor", ascending=True)
                
                if not df_chat.empty:
                    fig_chat = px.bar(
                        df_chat,
                        x='Valor',
                        y='Imposto',
                        orientation='h',
                        title="📊 Impostos Calculados",
                        color='Valor',
                        color_continuous_scale='Viridis'
                    )
                    fig_chat.update_traces(texttemplate='R$ %{x:,.0f}', textposition='outside')
                    fig_chat.update_layout(height=300, showlegend=False, coloraxis_showscale=False)
                    st.plotly_chart(fig_chat, use_container_width=True)
    
    # Input do chat
    user_input = st.chat_input("Digite sua pergunta...")
    
    if user_input:
        # Adicionar mensagem do usuário
        st.session_state["msgs"].append({"role": "user", "content": user_input})
        
        # Processar com LLM
        with st.spinner("🤔 Pensando..."):
            try:
                # Carregar relatório ativo
                rel = _load_active_report()
                
                # Preparar contexto
                context = ""
                if rel:
                    resumo = rel.get("resumo_executivo", {})
                    totais = rel.get("totais_por_imposto", {})
                    
                    context = f"""
RELATÓRIO ATIVO:
- Total de itens: {resumo.get('total_itens', 0)}
- Valor total calculado: R$ {resumo.get('total_calculado', 0):,.2f}
- Divergência: R$ {abs(resumo.get('divergencia_absoluta', 0)):,.2f}
- Nível de risco: {resumo.get('nivel_risco', 'BAIXO')}

IMPOSTOS CALCULADOS:
"""
                    for imp, dados in totais.items():
                        calc = dados.get("calculado", 0)
                        decl = dados.get("declarado", 0)
                        context += f"- {imp.upper()}: Calculado R$ {calc:,.2f}, Declarado R$ {decl:,.2f}\n"
                else:
                    context = "Nenhum relatório ativo no momento."
                
                # Montar histórico para OpenAI
                messages = [
                    {"role": "system", "content": f"""Você é um assistente fiscal especializado em impostos brasileiros.

{context}

INSTRUÇÕES:
- Responda de forma clara e profissional
- Use os dados do relatório quando relevante
- Se perguntarem sobre gráfico, diga "vou gerar o gráfico" e explique o que será mostrado
- Para dúvidas fiscais, use seu conhecimento sobre legislação brasileira
- Seja conciso mas completo
- Use formatação Markdown quando apropriado"""}
                ]
                
                # Adicionar histórico (últimas 10 mensagens)
                for msg in st.session_state["msgs"][-10:]:
                    if msg["role"] in ["user", "assistant"]:
                        messages.append({
                            "role": msg["role"],
                            "content": msg["content"]
                        })
                
                # Chamar OpenAI
                response = openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    max_tokens=2000,
                    temperature=0.7
                )
                
                answer = response.choices[0].message.content
                
                # Salvar resposta
                st.session_state["msgs"].append({"role": "assistant", "content": answer})
                
                # Verificar se deve gerar gráfico
                if any(palavra in user_input.lower() for palavra in ["gráfico", "grafico", "chart", "plot", "mostre", "visualize"]):
                    resultado_grafico = processar_pergunta_grafico(user_input, rel)
                    
                    if resultado_grafico["gerar_grafico"]:
                        fig = gerar_grafico_inteligente(
                            resultado_grafico["tipo"],
                            resultado_grafico["dados"],
                            user_input
                        )
                        
                        if fig:
                            st.session_state["msgs"].append({
                                "role": "chart",
                                "tipo": resultado_grafico["tipo"],
                                "dados": resultado_grafico["dados"]
                            })
            
            except Exception as e:
                error_msg = f"❌ Erro ao processar: {str(e)}"
                st.session_state["msgs"].append({"role": "assistant", "content": error_msg})
        
        # Rerun APENAS para atualizar o chat
        st.rerun()
    
    # Botão limpar histórico
    if st.button("🗑️ Limpar Histórico"):
        st.session_state["msgs"] = []
        st.rerun()

# ==================== ABA 3: NOTÍCIAS ====================

with aba_news:
    st.subheader("📰 Notícias e Atualizações Fiscais")
    st.caption("Últimas notícias sobre legislação tributária e reforma fiscal")
    
    # Botão atualizar
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🔄 Atualizar", use_container_width=True):
            with st.spinner("📡 Buscando..."):
                try:
                    news = get_news()
                    if news and len(news) > 0:
                        # Filtrar notícias válidas
                        news_validas = [
                            n for n in news 
                            if n.get('title') and n.get('title') not in ['N/A', 'Sem título', '']
                        ]
                        if len(news_validas) > 0:
                            st.session_state["news"] = news_validas
                            st.session_state["usar_api"] = True
                            st.success(f"✅ {len(news_validas)} notícias carregadas da API!")
                        else:
                            st.session_state["usar_api"] = False
                            st.info("ℹ️ Mostrando notícias de exemplo")
                    else:
                        st.session_state["usar_api"] = False
                        st.info("ℹ️ Mostrando notícias de exemplo")
                except Exception as e:
                    st.session_state["usar_api"] = False
                    st.info("ℹ️ Mostrando notícias de exemplo")
    
    # Decidir qual tipo mostrar
    usar_api = st.session_state.get("usar_api", False)
    news_list = st.session_state.get("news", [])
    
    # Se tem notícias da API E flag está ativa
    if usar_api and news_list and len(news_list) > 0:
        st.markdown("### 📰 Últimas Notícias (API)")
        for idx, noticia in enumerate(news_list[:10], 1):
            title = noticia.get('title', '')
            if not title:
                continue
            
            with st.expander(f"📰 {title}"):
                st.markdown(f"**Fonte:** {noticia.get('source', 'N/A')}")
                st.markdown(f"**Data:** {noticia.get('date', 'N/A')}")
                st.markdown(noticia.get('summary', 'Sem resumo'))
                
                if noticia.get('url'):
                    st.markdown(f"[🔗 Ler mais]({noticia['url']})")
    else:
        # SEMPRE mostrar notícias de exemplo
        st.markdown("### 📰 Notícias em Destaque")
    
        noticias_exemplo = [
            {
                "emoji": "🏛️",
                "titulo": "Reforma Tributária: CBS e IBS em vigor a partir de 2026",
                "fonte": "Receita Federal do Brasil",
                "data": "30/10/2025",
                "resumo": "A reforma tributária aprovada estabelece a implementação gradual dos novos impostos CBS e IBS, que substituirão PIS, COFINS, ICMS e ISS.",
                "url": "https://www.gov.br/receitafederal"
            },
            {
                "emoji": "📊",
                "titulo": "Nova versão da EFD-Reinf entra em vigor em dezembro",
                "fonte": "SPED - Sistema Público de Escrituração Digital",
                "data": "28/10/2025",
                "resumo": "Empresas devem se preparar para mudanças na escrituração fiscal digital. Prazo de adequação até 31/12/2025.",
                "url": "https://sped.rfb.gov.br"
            },
            {
                "emoji": "💼",
                "titulo": "Alíquota padrão do IVA será de 26,5%, diz Fazenda",
                "fonte": "Ministério da Fazenda",
                "data": "25/10/2025",
                "resumo": "Governo confirma alíquota padrão do novo IVA dual (CBS + IBS). Alguns setores terão redução ou isenção.",
                "url": "https://www.gov.br/fazenda"
            },
            {
                "emoji": "🏪",
                "titulo": "Simples Nacional: novas regras para 2026",
                "fonte": "Receita Federal",
                "data": "20/10/2025",
                "resumo": "Mudanças nos limites de faturamento e nas alíquotas do Simples Nacional entram em vigor em janeiro.",
                "url": "https://www8.receita.fazenda.gov.br/simplesnacional"
            }
        ]
        
        for noticia in noticias_exemplo:
            with st.expander(f"{noticia['emoji']} {noticia['titulo']}"):
                st.markdown(f"**Fonte:** {noticia['fonte']}")
                st.markdown(f"**Data:** {noticia['data']}")
                st.markdown(noticia['resumo'])
                st.markdown(f"[🔗 Ler mais]({noticia['url']})")
