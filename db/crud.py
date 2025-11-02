from __future__ import annotations
import csv, json, math, os
from typing import Any, Dict, List, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from .models import (
    NotaFiscal as NF,
    NotaFiscalItem as NFItem,
    ImpostoDeclarado as DeclaradoDB,
    ImpostoCalculado as CalculadoDB,
    Divergencia as DivergenciaDB,
    Etapa as EtapaDB,
    Relatorio as RelatorioDB,
    ChatMessageDB,
)

__all__ = [
    "save_nf_full",
    "save_chat",
    "save_nf_csv_auto",
    "save_nf_cabecalho_csv",
    "save_nf_itens_csv",
]

# ------------------- utilidades CSV -------------------
def _norm(s: str | None) -> str:
    return (s or "").strip().lower()

def _get_opt(data: Dict[str, Any] | None, *cands: str) -> Optional[str]:
    if not data:
        return None
    lower = {_norm(k): k for k in data.keys()}
    for c in cands:
        k = lower.get(_norm(c))
        if k is not None:
            val = data[k]
            return str(val).strip() if val is not None else None
    return None

def _to_float(x) -> Optional[float]:
    try:
        if x in (None, "", "nan"):
            return None
        if isinstance(x, str):
            s = x.replace(".", "").replace(",", ".")
        else:
            s = x
        v = float(s)
        if math.isnan(v):
            return None
        return v
    except Exception:
        return None

def _load_csv_rows(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return [dict(r) for r in reader]

def _is_items_csv(rows: List[Dict[str, Any]]) -> bool:
    if not rows:
        return False
    sample = {_norm(k) for k in rows[0].keys()}
    # heurística: itens têm nitem/xprod/cprod/cfop/ncm OU seus equivalentes em PT-BR
    return any(k in sample for k in [
        "nitem","xprod","cprod","cfop","ncm",
        "número produto","numero produto","descrição do produto/serviço","descricao do produto/servico",
        "código ncm/sh","codigo ncm/sh","ncm/sh","quantidade","valor unitário","valor unitario","valor total"
    ])

# ------------------- CSV → banco -------------------
def _find_or_create_nf_by_chave(db: Session, chave: Optional[str], defaults: Dict[str, Any]) -> NF:
    nf = None
    if chave:
        nf = db.query(NF).filter(NF.chave == chave).one_or_none()
    if nf is None:
        allowed = {
            "chave","numero","serie","emitente_cnpj","emitente_nome",
            "destinatario_cnpj","destinatario_nome","uf_origem","uf_destino",
            "municipio_servico","uf_servico","data_emissao","total_nf"
        }
        payload = {k: v for k, v in (defaults or {}).items() if k in allowed}
        nf = NF(**payload)
        db.add(nf)
        db.flush()
    else:
        for k, v in (defaults or {}).items():
            if hasattr(nf, k) and getattr(nf, k, None) in (None, "") and v not in (None, ""):
                setattr(nf, k, v)
    return nf

def save_nf_cabecalho_csv(db: Session, path: str) -> int:
    rows = _load_csv_rows(path)
    if not rows:
        return 0

    merged: Dict[str, Any] = {}
    for r in rows:
        for k, v in r.items():
            if (k not in merged) or merged[k] in (None, "", "nan"):
                merged[k] = v

    chave = _get_opt(merged, "CHAVE DE ACESSO", "chNFe", "chave_nfe", "chavenfe", "chave")
    numero = _get_opt(merged, "NÚMERO", "NUMERO", "nNF", "numero", "numnf")
    serie  = _get_opt(merged, "SÉRIE", "SERIE", "serie", "nSerie", "nserie")
    emit_cnpj = _get_opt(merged, "CPF/CNPJ EMITENTE", "CNPJ_emitente", "emit_cnpj", "cnpj_emit", "cnpj")
    dest_cnpj = _get_opt(merged, "CNPJ DESTINATÁRIO", "CNPJ DESTINATARIO", "dest_cnpj", "cnpj_dest", "cnpjdest")
    dt_emis   = _get_opt(merged, "DATA EMISSÃO", "DATA EMISSAO", "dhEmi", "dEmi", "data_emissao", "emissao")
    vtotal    = _get_opt(merged, "VALOR NOTA FISCAL", "vNF", "valor_total", "total_nf", "vTotNF", "total")
    uf_origem = _get_opt(merged, "UF EMITENTE", "UF EMIT", "UF_EMIT", "UF EMITENTE ")
    uf_dest   = _get_opt(merged, "UF DESTINATÁRIO", "UF DESTINATARIO", "UF_DEST", "UF DESTINATARIO ")

    defaults = dict(
        chave=chave, numero=numero, serie=serie,
        emitente_cnpj=emit_cnpj, destinatario_cnpj=dest_cnpj,
        data_emissao=dt_emis, total_nf=vtotal,
        uf_origem=uf_origem, uf_destino=uf_dest,
    )
    nf = _find_or_create_nf_by_chave(db, chave, defaults)
    db.commit()
    return nf.id

def save_nf_itens_csv(db: Session, path: str, chave_hint: Optional[str] = None) -> int:
    rows = _load_csv_rows(path)
    if not rows:
        return 0

    sample = rows[0]
    chave = chave_hint or _get_opt(sample, "CHAVE DE ACESSO", "chNFe", "chave_nfe", "chavenfe", "chave")
    numero = _get_opt(sample, "NÚMERO", "NUMERO", "nNF", "numero", "numnf")
    serie  = _get_opt(sample, "SÉRIE", "SERIE", "serie", "nSerie", "nserie")

    defaults = dict(chave=chave, numero=numero, serie=serie)
    nf = _find_or_create_nf_by_chave(db, chave, defaults)

    for r in rows:
        item = NFItem(
            nota_id=nf.id,

            # número do item
            n_item=_get_opt(
                r,
                "NÚMERO PRODUTO", "NUMERO PRODUTO",
                "nItem", "item", "item_seq"
            ),

            # código
            codigo=_get_opt(
                r,
                "CÓDIGO PRODUTO", "CODIGO PRODUTO",
                "cProd", "cod", "codigo", "prod_codigo"
            ),

            # descrição
            descricao=_get_opt(
                r,
                "DESCRIÇÃO DO PRODUTO/SERVIÇO", "DESCRICAO DO PRODUTO/SERVICO",
                "xProd", "desc", "descricao", "produto_descricao"
            ),

            # ncm
            ncm=_get_opt(
                r,
                "CÓDIGO NCM/SH", "CODIGO NCM/SH", "NCM/SH",
                "NCM", "ncm"
            ),

            # cfop
            cfop=_get_opt(r, "CFOP", "cfop"),

            # campos ISS (se vierem — opcionais, não quebram se faltarem)
            subitem_lc116=_get_opt(r, "subitem_lc116", "subitem", "lc116_subitem", "servico_subitem"),
            municipio_servico=_get_opt(r, "municipio_servico", "mun_servico", "municipio"),
            uf_servico=_get_opt(r, "uf_servico", "uf_serv", "uf"),

            # quantidade
            quantidade=_to_float(_get_opt(r, "QUANTIDADE", "Quantidade", "quantidade", "qCom", "qtd")),

            # valores
            valor_unitario=_to_float(_get_opt(r, "VALOR UNITÁRIO", "VALOR UNITARIO", "vUnCom", "vUnit", "valor_unit", "vl_unit")),
            valor_total=_to_float(_get_opt(r, "VALOR TOTAL", "vProd", "vTotal", "valor_total", "vl_total")),
        )
        db.add(item)

    db.commit()
    return nf.id

def save_nf_csv_auto(db: Session, path: str) -> Dict[str, Any]:
    rows = _load_csv_rows(path)
    if not rows:
        return {"tipo": "vazio", "nota_id": 0, "linhas": 0, "path": path}
    if _is_items_csv(rows):
        nid = save_nf_itens_csv(db, path)
        return {"tipo": "itens", "nota_id": nid, "linhas": len(rows), "path": path}
    else:
        nid = save_nf_cabecalho_csv(db, path)
        return {"tipo": "cabecalho", "nota_id": nid, "linhas": len(rows), "path": path}

# ------------------- Relatório consolidado → banco -------------------
def _get(d: Dict[str, Any] | None, key: str, default=None):
    if not d:
        return default
    return d.get(key, default)

def save_nf_full(
    db: Session,
    relatorio: Dict[str, Any],
    json_path: str,
    pdf_path: str | None = None,
    session_id: str = "default",
) -> int:
    nota = relatorio.get("nota") or {}

    chave = _get(nota, "chave")
    numero = _get(nota, "numero")
    serie  = _get(nota, "serie")
    emit   = _get(nota, "emitente_cnpj") or _get(nota, "cnpj_emitente")
    dest   = _get(nota, "destinatario_cnpj") or _get(nota, "cnpj_destinatario")
    dt_emis = _get(nota, "data_emissao")
    total_nf = _get(nota, "total_nf") or _get(nota, "valor_total")
    uf_origem = _get(nota, "uf_origem")
    uf_dest   = _get(nota, "uf_destino")

    defaults = dict(
        chave=chave, numero=numero, serie=serie,
        emitente_cnpj=emit, destinatario_cnpj=dest,
        data_emissao=dt_emis, total_nf=float(total_nf or 0.0),
        uf_origem=uf_origem, uf_destino=uf_dest,
    )
    nf = _find_or_create_nf_by_chave(db, chave, defaults)

    # Declarados (totais por imposto)
    for k, v in (nota.get("declarados") or {}).items():
        if v is None:
            continue
        try:
            valor = float(v)
        except Exception:
            continue
        db.add(DeclaradoDB(nota_id=nf.id, imposto=str(k), valor=valor))

    # Calculados (totais por imposto)
    for k, v in (relatorio.get("calculados") or {}).items():
        if v is None:
            continue
        if isinstance(v, dict) and "total" in v:
            v = v["total"]
        try:
            valor = float(v)
        except Exception:
            continue
        db.add(CalculadoDB(nota_id=nf.id, imposto=str(k), valor=valor))

    # Divergências
    for d in (relatorio.get("divergencias") or []):
        imposto = d.get("imposto") or d.get("tax") or None
        tipo = d.get("tipo") or d.get("agent") or "divergencia"
        msg = d.get("mensagem") or d.get("message") or json.dumps(d, ensure_ascii=False)
        vdecl = _to_float(d.get("valor_decl") or d.get("declarado"))
        vcalc = _to_float(d.get("valor_calc") or d.get("calculado"))
        db.add(DivergenciaDB(nota_id=nf.id, imposto=imposto, tipo=str(tipo), mensagem=msg,
                             valor_decl=vdecl or 0.0, valor_calc=vcalc or 0.0))

    # Etapas
    for e in (relatorio.get("etapas") or []):
        etapa = str(e.get("etapa") or e.get("nome") or e.get("step") or "")
        ts = str(e.get("ts") or datetime.utcnow().isoformat())
        db.add(EtapaDB(nota_id=nf.id, etapa=etapa, ts=ts))

    # Relatório (tabela Relatorio)
    db.add(RelatorioDB(nota_id=nf.id, session_id=session_id, json_path=json_path))

    db.commit()
    return nf.id

def save_chat(db: Session, session_id: str, role: str, content: str) -> None:
    db.add(ChatMessageDB(session_id=session_id, role=role, content=content,
                         ts=datetime.utcnow().isoformat()))
    db.commit()
