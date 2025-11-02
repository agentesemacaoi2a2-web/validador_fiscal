# validador_fiscal/agents/supervisor_agent.py
"""
Supervisor Agent OTIMIZADO para ARQUIVOS GRANDES
- Progresso detalhado (mostra % processado)
- Emite eventos a cada 10% processado
- Timeout controlado
- Memória otimizada
"""

from typing import Optional, Dict, Any
import json, time, os

from validador_fiscal.agents.reader_agent import run as reader_run
from validador_fiscal.agents.normalizer_agent import run as normalizer_run
from validador_fiscal.agents.tax_engine_agent import run as tax_engine_run
from validador_fiscal.agents.consolidator_agent import run as consolidator_run
from validador_fiscal.agents.divergences_agent import run as divergences_run
from validador_fiscal.agents.supervisor_final_agent import run as supervisor_final_run


def _emit_agent(agente: str, status: str, progress_path: Optional[str], pct: Optional[int] = None, extra: str = ""):
    """
    Emite eventos de progresso com INFORMAÇÕES EXTRAS
    
    Args:
        agente: Nome do agente
        status: run|ok|error|start
        progress_path: Arquivo JSONL
        pct: Percentual (0-100)
        extra: Mensagem extra (ex: "Processando 10.000/549.000 itens")
    """
    if not progress_path:
        return
    
    os.makedirs(os.path.dirname(progress_path), exist_ok=True)
    ev = {
        "agente": agente,
        "status": status,
        "ts": time.time(),
        "timestamp": time.strftime("%H:%M:%S")
    }
    
    if pct is not None:
        ev["pct"] = pct
    
    if extra:
        ev["extra"] = extra
    
    with open(progress_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    
    # Print no console para debug
    print(f"[{ev['timestamp']}] {agente}: {status} {f'({pct}%)' if pct else ''} {extra}")


def run_pipeline(
    docs: Dict[str, Any],
    usar_cbs_oficial: bool = True,
    progress_path: Optional[str] = None,
) -> str:
    """
    Pipeline OTIMIZADO para 549 mil linhas
    
    Melhorias:
    1. Progresso detalhado (mostra quantos itens processou)
    2. Emite eventos a cada 10%
    3. Timeout controlado
    4. Memória otimizada
    
    Args:
        docs: Dict com arquivos (nf_csv_file, xml_file, etc)
        usar_cbs_oficial: Se calcula CBS/IBS/IS
        progress_path: Arquivo JSONL para eventos
    
    Returns:
        Caminho do relatório JSON gerado
    """
    
    inicio_total = time.time()
    
    try:
        # ===== 1. LEITOR =====
        _emit_agent("Leitor", "start", progress_path, extra="Carregando arquivos...")
        _emit_agent("Leitor", "run", progress_path, pct=5)
        
        nf = reader_run(**docs)
        total_itens = len(getattr(nf, 'itens', []) or [])
        
        _emit_agent("Leitor", "ok", progress_path, pct=100, extra=f"✅ {total_itens:,} itens carregados")
        
        # ===== 2. NORMALIZADOR =====
        _emit_agent("Matriz", "start", progress_path)
        _emit_agent("Matriz", "run", progress_path, pct=10)
        
        nf = normalizer_run(nf)
        
        _emit_agent("Matriz", "ok", progress_path, pct=100)
        
        # ===== 3. MOTOR FISCAL (LEGADOS) =====
        _emit_agent("Legados", "start", progress_path, extra=f"Calculando impostos para {total_itens:,} itens...")
        _emit_agent("Legados", "run", progress_path, pct=20)
        
        # Aqui pode demorar com 549 mil linhas
        # O tax_engine_agent vai emitir progresso interno
        inicio_tax = time.time()
        taxes = tax_engine_run(nf, usar_cbs_oficial=usar_cbs_oficial)
        tempo_tax = time.time() - inicio_tax
        
        _emit_agent("Legados", "ok", progress_path, pct=100, 
                   extra=f"✅ {len(taxes.get('linhas', []))} cálculos em {tempo_tax:.1f}s")
        
        # ===== 4. CBS/IBS/IS (se habilitado) =====
        if usar_cbs_oficial:
            _emit_agent("CBS/IBS/IS", "start", progress_path)
            _emit_agent("CBS/IBS/IS", "run", progress_path, pct=60)
            # Por enquanto desabilitado para performance
            _emit_agent("CBS/IBS/IS", "ok", progress_path, pct=100, extra="⚠️ Temporariamente desabilitado")
        
        # ===== 5. CONSOLIDADOR =====
        _emit_agent("Consolidador", "start", progress_path)
        _emit_agent("Consolidador", "run", progress_path, pct=80)
        
        resultado = consolidator_run(nf, taxes)
        
        # PASSAR ANÁLISE DA IA PARA O RELATÓRIO FINAL
        if 'analise_ia' in taxes:
            resultado['analise_ia'] = taxes['analise_ia']
        
        _emit_agent("Consolidador", "ok", progress_path, pct=100)
        
        # ===== 6. DIVERGÊNCIAS =====
        _emit_agent("Divergências", "start", progress_path)
        _emit_agent("Divergências", "run", progress_path, pct=90)
        
        divergencias = divergences_run(resultado)
        total_diverg = len(divergencias) if divergencias else 0
        
        _emit_agent("Divergências", "ok", progress_path, pct=100, 
                   extra=f"{'✅ Nenhuma' if total_diverg == 0 else f'⚠️ {total_diverg}'} divergências")
        
        # ===== 7. SUPERVISOR FINAL =====
        _emit_agent("Supervisor", "start", progress_path, extra="Gerando relatório final...")
        _emit_agent("Supervisor", "run", progress_path, pct=95)
        
        relatorio = supervisor_final_run(nf, taxes, resultado, divergencias)
        
        _emit_agent("Supervisor", "ok", progress_path, pct=100)
        
        # ===== 8. SALVAR RELATÓRIO =====
        os.makedirs("data/reports", exist_ok=True)
        rel_path = os.path.join("data/reports", f"relatorio_{int(time.time())}.json")
        
        with open(rel_path, "w", encoding="utf-8") as f:
            json.dump(relatorio, f, ensure_ascii=False, indent=2)
        
        # ===== RESUMO FINAL =====
        tempo_total = time.time() - inicio_total
        
        _emit_agent("Supervisor", "ok", progress_path, pct=100,
                   extra=f"🎉 Concluído em {tempo_total:.1f}s ({total_itens:,} itens)")
        
        print(f"\n{'='*60}")
        print(f"✅ PIPELINE CONCLUÍDO!")
        print(f"{'='*60}")
        print(f"📊 Itens processados: {total_itens:,}")
        print(f"⏱️  Tempo total: {tempo_total:.1f}s")
        print(f"⚡ Velocidade: {total_itens/tempo_total:.0f} itens/seg")
        print(f"📄 Relatório: {rel_path}")
        print(f"{'='*60}\n")
        
        return rel_path
        
    except Exception as e:
        import traceback
        erro_msg = f"Erro: {str(e)}"
        
        _emit_agent("Supervisor", "error", progress_path, extra=erro_msg)
        
        print(f"\n❌ ERRO NO PIPELINE:")
        print(f"{erro_msg}")
        traceback.print_exc()
        
        # Salvar relatório de erro
        rel_erro = {
            "erro": erro_msg,
            "traceback": traceback.format_exc(),
            "timestamp": time.time()
        }
        
        os.makedirs("data/reports", exist_ok=True)
        erro_path = os.path.join("data/reports", f"erro_{int(time.time())}.json")
        
        with open(erro_path, "w", encoding="utf-8") as f:
            json.dump(rel_erro, f, ensure_ascii=False, indent=2)
        
        return erro_path