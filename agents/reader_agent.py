from typing import Optional
from validador_fiscal.tools.nf_parse_tool import parse_any, NotaFiscal

def run(nf_csv_file: Optional[str] = None,
        xml_file: Optional[str] = None,
        pdf_file: Optional[str] = None,
        image_file: Optional[str] = None) -> NotaFiscal:
    """Leitura unificada, usada como AGENTE de entrada."""
    return parse_any(nf_csv_file=nf_csv_file, xml_file=xml_file, pdf_file=pdf_file, image_file=image_file)
