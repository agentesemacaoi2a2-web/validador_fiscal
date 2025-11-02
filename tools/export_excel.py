import pandas as pd
import os

def gerar_excel(relatorio: dict, output_path: str):
    """
    Gera um Excel com 2 abas:
      - Calculados (totais dos impostos)
      - Divergencias (tabela de divergências item a item)
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # TAB 1: Totais
    calculados = relatorio.get("calculados", {})
    df_calc = (
        pd.DataFrame(list(calculados.items()), columns=["Imposto", "Valor Calculado"])
        if calculados else pd.DataFrame(columns=["Imposto", "Valor Calculado"])
    )

    # TAB 2: Divergências
    divergencias = relatorio.get("divergencias", [])
    df_div = pd.DataFrame(divergencias) if divergencias else pd.DataFrame(columns=["imposto","declarado","calculado","diferenca"])

    # Grava
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df_calc.to_excel(writer, sheet_name="Totais", index=False)
        df_div.to_excel(writer, sheet_name="Divergencias", index=False)

    return output_path
