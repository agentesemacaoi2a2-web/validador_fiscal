import os
import io
import pandas as pd
import pdfplumber
from lxml import etree
from PIL import Image

# OCR opcional
try:
    import pytesseract
    _HAS_TESS = True
except Exception:
    pytesseract = None
    _HAS_TESS = False

from validador_fiscal.core.models import NotaFiscal, Item, Declarados

# ---------------- CSV universal (encoding + separador) ----------------
def _read_csv_smart(path):
    encs = ["utf-8", "utf-8-sig", "latin1", "cp1252", "iso-8859-1"]
    for enc in encs:
        try:
            return pd.read_csv(path, encoding=enc, sep=None, engine="python", dtype=str)
        except Exception:
            pass
    with open(path, "rb") as f:
        data = f.read().decode("latin1", "replace")
    return pd.read_csv(io.StringIO(data), sep=None, engine="python", dtype=str)

def _tf_from_df(df, col):
    try:
        return float(df[col].iloc[0]) if col in df.columns else None
    except Exception:
        return None

def _tf_xml_val(root, xpath, ns):
    v = root.findtext(xpath, namespaces=ns)
    try:
        return float(v) if v else None
    except Exception:
        return None

# ---------------- CSV → NotaFiscal ----------------
def parse_csv(nf_csv_path: str) -> NotaFiscal:
    df = _read_csv_smart(nf_csv_path)
    itens = []
    for i, r in df.iterrows():
        itens.append(Item(
            codigo=str(r.get('codigo') or r.get('cod') or r.get('item') or i),
            descricao=str(r.get('descricao') or ''),
            ncm=str(r.get('ncm') or ''),
            cfop=str(r.get('cfop') or ''),
            subitem_lc116=str(r.get('subitem_lc116') or ''),
            quantidade=float(r.get('qtd') or r.get('quantidade') or 1),
            valor_unitario=float(r.get('vl_unit') or r.get('valor_unitario') or 0),
            valor_total=float(r.get('vl_total') or r.get('valor_total') or 0),
        ))
    muni = str(df.get('cod_ibge_municipio_iss')[0]) if 'cod_ibge_municipio_iss' in df.columns else None
    d = Declarados(
        icms=_tf_from_df(df, 'vICMS'),
        ipi=_tf_from_df(df, 'vIPI'),
        pis=_tf_from_df(df, 'vPIS'),
        cofins=_tf_from_df(df, 'vCOFINS'),
        iss=_tf_from_df(df, 'vISS'),
        irpj=_tf_from_df(df, 'vIRPJ'),
        csll=_tf_from_df(df, 'vCSLL'),
    )
    return NotaFiscal(itens=itens, declarados=d, municipio_iss_ibge=muni)

# ---------------- XML → NotaFiscal ----------------
def parse_xml(nfe_xml_path: str) -> NotaFiscal:
    parser = etree.XMLParser(recover=True, encoding='utf-8')
    root = etree.parse(nfe_xml_path, parser)
    ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
    numero = root.findtext('.//nfe:ide/nfe:nNF', namespaces=ns) or ""
    itens = []
    for det in root.findall('.//nfe:det', namespaces=ns):
        prod = det.find('nfe:prod', namespaces=ns)
        if prod is None:
            continue
        itens.append(Item(
            codigo=prod.findtext('nfe:cProd', namespaces=ns) or '',
            descricao=prod.findtext('nfe:xProd', namespaces=ns) or '',
            ncm=prod.findtext('nfe:NCM', namespaces=ns) or '',
            cfop=prod.findtext('nfe:CFOP', namespaces=ns) or '',
            quantidade=float(prod.findtext('nfe:qCom', namespaces=ns) or 1),
            valor_unitario=float(prod.findtext('nfe:vUnCom', namespaces=ns) or 0),
            valor_total=float(prod.findtext('nfe:vProd', namespaces=ns) or 0),
        ))
    d = Declarados(
        icms=_tf_xml_val(root, './/nfe:ICMS//nfe:vICMS', ns),
        ipi=_tf_xml_val(root, './/nfe:IPI//nfe:vIPI', ns),
        pis=_tf_xml_val(root, './/nfe:PIS//nfe:vPIS', ns),
        cofins=_tf_xml_val(root, './/nfe:COFINS//nfe:vCOFINS', ns),
        iss=_tf_xml_val(root, './/nfe:ISSQN//nfe:vISSQN', ns),
    )
    return NotaFiscal(numero=numero, itens=itens, declarados=d)

# ---------------- PDF/Imagem → OCR ----------------
def parse_pdf_or_image(path: str) -> NotaFiscal:
    if not _HAS_TESS:
        raise RuntimeError("OCR de imagem requer Tesseract instalado e configurado.")
    ext = os.path.splitext(path)[1].lower()
    if ext == '.pdf':
        text = ''
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ''
    else:
        img = Image.open(path)
        text = pytesseract.image_to_string(img, lang='por')
    # Heurística mínima – item único, valor será checado por auditor posteriormente
    return NotaFiscal(itens=[Item(codigo='OCR', descricao='Documento OCR', valor_total=0.0)])
