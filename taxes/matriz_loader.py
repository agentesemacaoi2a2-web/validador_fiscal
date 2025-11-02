import os
import sqlite3
import pandas as pd

# Caminho do SQLite via .env (se não existir, o loader cai para CSVs)
MATRIZ_DB_PATH = os.getenv('MATRIZ_DB_PATH', 'db/matriz.db')
MATRIZ_DIR = os.getenv('MATRIZ_DIR', 'data/matriz')

# SELECTs mantêm os MESMOS nomes de colunas dos CSVs originais
_SQL = {
    'federais': """
        SELECT tributo, aliquota, base_calculo, observacao
        FROM federais;
    """,
    'icms_uf': """
        SELECT uf, aliquota, base_calculo, observacao
        FROM icms_uf;
    """,
    'icms_inter': """
        SELECT uf_origem, uf_destino, aliquota, base_calculo, observacao
        FROM icms_interestadual;
    """,
    'iss': """
        SELECT cod_ibge, subitem_lc116, aliquota_iss, observacao
        FROM iss_full;
    """,
    'iss_fallback': """
        SELECT cod_ibge, subitem_lc116, aliquota_iss, fonte
        FROM iss_fallback;
    """,
}

def _read_sql(name: str) -> pd.DataFrame:
    path = MATRIZ_DB_PATH
    if not os.path.exists(path):
        return pd.DataFrame()
    try:
        with sqlite3.connect(path) as con:
            return pd.read_sql_query(_SQL[name], con)
    except Exception:
        return pd.DataFrame()

def _load_csv(name: str) -> pd.DataFrame:
    path = os.path.join(MATRIZ_DIR, name)
    if not os.path.exists(path):
        return pd.DataFrame()
    try:
        return pd.read_csv(path, dtype=str)
    except Exception:
        return pd.DataFrame()

def load_matriz() -> dict:
    """
    Prioridade:
      1) Banco SQLite (MATRIZ_DB_PATH), se existir e tiver as tabelas
      2) CSVs (MATRIZ_DIR), como fallback 1:1 com seu projeto original
    A interface retorna DataFrames com os mesmos campos de antes.
    """
    df_fed  = _read_sql('federais')
    df_uf   = _read_sql('icms_uf')
    df_inter= _read_sql('icms_inter')
    df_iss  = _read_sql('iss')
    df_issf = _read_sql('iss_fallback')

    # Fallback por dataset se vier vazio
    if df_fed.empty:   df_fed = _load_csv('Federais.csv')
    if df_uf.empty:    df_uf = _load_csv('ICMS_uf.csv')
    if df_inter.empty: df_inter = _load_csv('ICMS_interestadual.csv')
    if df_iss.empty:   df_iss = _load_csv('ISS_full_schema.csv')
    if df_issf.empty:  df_issf = _load_csv('ISS_external_reference.csv')
    
    # Novos: ST e DIFAL
    df_st = _load_csv('ST_MVA.csv')
    df_difal = _load_csv('DIFAL.csv')

    return {
        'federais': df_fed,
        'icms_uf': df_uf,
        'icms_inter': df_inter,
        'iss': df_iss,
        'iss_fallback': df_issf,
        'st_mva': df_st,
        'difal': df_difal,
    }
