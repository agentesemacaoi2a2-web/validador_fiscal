from __future__ import annotations
import os, csv
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

import pandas as pd
from lxml import etree
import pdfplumber
from PIL import Image

try:
    import pytesseract
    _HAS_TESS = True
except Exception:
    _HAS_TESS = False

@dataclass
class Declarados:
    icms: float = 0.0
    st: float = 0.0
    difal: float = 0.0
    ipi: float = 0.0
    pis: float = 0.0
    cofins: float = 0.0
    iss: float = 0.0
    irpj: float = 0.0
    csll: float = 0.0
    cbs: float = 0.0
    ibs: float = 0.0
    is_: float = 0.0

@dataclass
class Item:
    codigo: str = ""
    descricao: str = ""
    ncm: str = ""
    cfop: str = ""
    quantidade: float = 0.0
    valor_unitario: float = 0.0
    valor_total: float = 0.0

@dataclass
class NotaFiscal:
    chave: Optional[str] = None
    numero: Optional[str] = None
    serie: Optional[str] = None
    data_emissao: Optional[str] = None
    emitente_cnpj: Optional[str] = None
    emitente_nome: Optional[str] = None
    destinatario_cnpj: Optional[str] = None
    destinatario_nome: Optional[str] = None
    destinatario_cpf: Optional[str] = None
    emissor_uf: Optional[str] = None
    destinatario_uf: Optional[str] = None
    itens: List[Item] = field(default_factory=list)
    declarados: Declarados = field(default_factory=Declarados)

def _try_float(x) -> float:
    try:
        if x is None or (isinstance(x, float) and pd.isna(x)):
            return 0.0
        return float(str(x).replace(",", "."))
    except Exception:
        return 0.0

def _sniff_csv(path: str) -> Dict[str, Any]:
    import chardet
    with open(path, "rb") as f:
        raw = f.read(65536)
    enc = chardet.detect(raw).get("encoding") or "ISO-8859-1"
    sample = raw.decode(enc, errors="ignore")
    dialect = csv.Sniffer().sniff(sample.splitlines()[0][:1024] + ",", delimiters=";,|\t,")
    return {"encoding": enc, "sep": dialect.delimiter}

def _parse_csv_any(nf_csv_file: str) -> NotaFiscal:
    """
    OTIMIZADO para arquivos grandes (549 mil linhas)
    - Leitura em chunks
    - Memória controlada
    - Progresso detalhado
    """
    
    print(f"📂 Lendo CSV: {os.path.basename(nf_csv_file)}...")
    
    cfg = _sniff_csv(nf_csv_file)
    
    # Ler apenas cabeçalho primeiro (1 linha)
    df_head = pd.read_csv(
        nf_csv_file, 
        encoding=cfg["encoding"], 
        sep=cfg["sep"], 
        engine="python",
        nrows=1  # Só primeira linha
    )

    cols = {c.strip().upper(): c for c in df_head.columns}
    def col(*names):
        for n in names:
            if n in cols: return cols[n]
        return None

    nf = NotaFiscal()
    
    # Extrair dados do cabeçalho
    ch_col = col("CHAVE DE ACESSO", "CHAVE")
    nf.chave = str(df_head[ch_col].iloc[0]).strip() if ch_col else None
    nf.numero = str(df_head.get(col("NÚMERO","NUMERO","NR"), [None])[0]).strip() if col("NÚMERO","NUMERO","NR") else None
    nf.serie  = str(df_head.get(col("SÉRIE","SERIE"), [None])[0]).strip() if col("SÉRIE","SERIE") else None
    nf.data_emissao = str(df_head.get(col("DATA EMISSÃO","DATA EMISSAO"), [None])[0]).strip() if col("DATA EMISSÃO","DATA EMISSAO") else None
    nf.emitente_cnpj = str(df_head.get(col("CPF/CNPJ EMITENTE","CNPJ EMITENTE"), [None])[0]).strip() if col("CPF/CNPJ EMITENTE","CNPJ EMITENTE") else None
    nf.destinatario_cnpj = str(df_head.get(col("CNPJ DESTINATÁRIO","CNPJ DESTINATARIO"), [None])[0]).strip() if col("CNPJ DESTINATÁRIO","CNPJ DESTINATARIO") else None
    nf.emissor_uf = str(df_head.get(col("UF EMITENTE"), [None])[0]).strip() if col("UF EMITENTE") else None
    nf.destinatario_uf = str(df_head.get(col("UF DESTINATÁRIO","UF DESTINATARIO"), [None])[0]).strip() if col("UF DESTINATÁRIO","UF DESTINATARIO") else None

    # Buscar arquivo de itens
    base = os.path.dirname(nf_csv_file)
    cand = [p for p in os.listdir(base) if p.lower().endswith(".csv") and "item" in p.lower()]
    
    itens_df = None
    if cand:
        p2 = os.path.join(base, cand[0])
        print(f"📦 Lendo itens: {os.path.basename(p2)}...")
        
        cfg2 = _sniff_csv(p2)
        
        # OTIMIZAÇÃO: Ler em chunks de 50 mil linhas
        chunk_size = 50000
        chunks = []
        
        total_linhas = sum(1 for _ in open(p2, encoding=cfg2["encoding"])) - 1  # -1 para header
        print(f"📊 Total de itens: {total_linhas:,}")
        
        if total_linhas > chunk_size:
            # Arquivo GRANDE - ler em chunks
            print(f"⚡ Processando em chunks de {chunk_size:,} linhas...")
            
            for idx, chunk in enumerate(pd.read_csv(
                p2, 
                encoding=cfg2["encoding"], 
                sep=cfg2["sep"], 
                engine="python",
                chunksize=chunk_size
            ), 1):
                chunks.append(chunk)
                processados = min(idx * chunk_size, total_linhas)
                pct = (processados / total_linhas * 100)
                print(f"   Chunk {idx}: {processados:,}/{total_linhas:,} ({pct:.0f}%)")
            
            # Concatenar todos os chunks
            itens_df = pd.concat(chunks, ignore_index=True)
            print(f"✅ {len(itens_df):,} itens carregados")
        else:
            # Arquivo pequeno - ler direto
            itens_df = pd.read_csv(p2, encoding=cfg2["encoding"], sep=cfg2["sep"], engine="python")
            print(f"✅ {len(itens_df):,} itens carregados")

    def build_items(d):
        """Constrói lista de itens - OTIMIZADO"""
        c = {c.strip().upper(): c for c in d.columns}
        def C(*names):
            for n in names:
                if n in c: return c[n]
            return None
        
        items = []
        total = len(d)
        
        print(f"🔨 Construindo {total:,} objetos Item...")
        
        for idx, (_, r) in enumerate(d.iterrows(), 1):
            items.append(Item(
                codigo=str(r.get(C("NÚMERO PRODUTO","NUMERO PRODUTO","CODIGO","CÓDIGO","COD"), "")),
                descricao=str(r.get(C("DESCRIÇÃO DO PRODUTO/SERVIÇO","DESCRICAO","DESCRICAO PRODUTO"), ""))[:200],
                ncm=str(r.get(C("CÓDIGO NCM/SH","CODIGO NCM/SH","NCM","NCM/SH (TIPO DE PRODUTO)"), "")),
                cfop=str(r.get(C("CFOP"), "")),
                quantidade=_try_float(r.get(C("QUANTIDADE","QTD","QCOM","QUANTID"), 0)),
                valor_unitario=_try_float(r.get(C("VALOR UNITÁRIO","VALOR UN","VUNCOM","VALOR_UNITARIO","VALOR UN "), 0)),
                valor_total=_try_float(r.get(C("VALOR TOTAL","VALOR TO","VALOR TOTL","VPROD","VALOR_TOTAL","VALOR TO"), 0)),
            ))
            
            # Mostrar progresso a cada 10%
            if idx % max(1, total // 10) == 0:
                pct = (idx / total * 100)
                print(f"   Progresso: {idx:,}/{total:,} ({pct:.0f}%)")
        
        print(f"✅ {len(items):,} itens construídos")
        # DEBUG
        if items:
            print(f"\n🔍 DEBUG - Primeiros 3 itens:")
            for idx, item in enumerate(items[:3], 1):
                print(f"   Item {idx}: valor_total={item.valor_total}, quantidade={item.quantidade}, ncm={item.ncm}, cfop={item.cfop}")
        return items

    if itens_df is not None:
        nf.itens = build_items(itens_df)
    else:
        # Tentar ler itens do mesmo CSV (cabeçalho)
        if {"NÚMERO PRODUTO","DESCRIÇÃO DO PRODUTO/SERVIÇO"}.issubset(set(cols)):
            nf.itens = build_items(df_head)

    # Ler impostos declarados - SOMAR de TODAS as linhas
    d = Declarados()
    
    # Se tem itens_df (arquivo de itens separado), usa ele
    df_para_somar = itens_df if itens_df is not None else df_head
    
    for label, attr in [
        ("ICMS","icms"), ("ST","st"), ("DIFAL","difal"), ("IPI","ipi"),
        ("PIS","pis"), ("COFINS","cofins"), ("ISS","iss"),
        ("IRPJ","irpj"), ("CSLL","csll"),
        ("CBS","cbs"), ("IBS","ibs"), ("IS","is_")
    ]:
        # Procurar coluna com padrões: "ICMS", "VALOR ICMS", "VALOR_ICMS", etc
        col_patterns = [label, f"VALOR {label}", f"VALOR_{label}", f"V{label}"]
        c = None
        for pattern in col_patterns:
            c = col(pattern)
            if c:
                break
        
        if c and c in df_para_somar.columns:
            # SOMAR todos os valores da coluna
            try:
                total = df_para_somar[c].apply(_try_float).sum()
                setattr(d, attr, total)
            except Exception as e:
                print(f"   ⚠️ Erro ao somar {label}: {e}")
                setattr(d, attr, 0.0)
    
    nf.declarados = d
    
    print(f"✅ NotaFiscal construída: {len(nf.itens):,} itens")
    
    return nf

def _parse_xml(xml_file: str) -> NotaFiscal:
    """Lê XML COMPLETO com todos os itens"""
    ns = {"nfe": "http://www.portalfiscal.inf.br/nfe"}
    tree = etree.parse(xml_file)
    root = tree.getroot()
    
    def gx(xpath, base=root):
        try:
            el = base.find(xpath, namespaces=ns)
            return el.text if el is not None else None
        except:
            return None
    
    # Cabeçalho
    nf = NotaFiscal(
        chave=gx(".//nfe:chNFe"),
        numero=gx(".//nfe:ide/nfe:nNF"),
        serie=gx(".//nfe:ide/nfe:serie"),
        data_emissao=gx(".//nfe:ide/nfe:dhEmi"),
        emitente_cnpj=gx(".//nfe:emit/nfe:CNPJ"),
        emitente_nome=gx(".//nfe:emit/nfe:xNome"),
        destinatario_cnpj=gx(".//nfe:dest/nfe:CNPJ"),
        destinatario_cpf=gx(".//nfe:dest/nfe:CPF"),
        destinatario_nome=gx(".//nfe:dest/nfe:xNome"),
        emissor_uf=gx(".//nfe:emit/nfe:enderEmit/nfe:UF"),
        destinatario_uf=gx(".//nfe:dest/nfe:enderDest/nfe:UF"),
    )

    # Formatar CPF se vier sem pontuação
    if nf.destinatario_cpf and len(nf.destinatario_cpf) == 11:
        cpf = nf.destinatario_cpf
        nf.destinatario_cpf = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
    
    # Extrair ITENS
    itens = []
    for det in root.findall(".//nfe:det", namespaces=ns):
        prod = det.find("nfe:prod", namespaces=ns)
        if prod is None:
            continue
        
        itens.append(Item(
            codigo=gx("nfe:cProd", prod) or "",
            descricao=gx("nfe:xProd", prod) or "",
            ncm=gx("nfe:NCM", prod) or "",
            cfop=gx("nfe:CFOP", prod) or "",
            quantidade=_try_float(gx("nfe:qCom", prod)),
            valor_unitario=_try_float(gx("nfe:vUnCom", prod)),
            valor_total=_try_float(gx("nfe:vProd", prod)),
        ))
    
    nf.itens = itens

    # Pegar valor total da nota COM desconto
    total_nf_xml = gx(".//nfe:ICMSTot/nfe:vNF", root)
    nf.total_produtos = float(total_nf_xml) if total_nf_xml else sum(item.valor_total for item in itens)
    
    print(f"   💰 Valor Total NF: R$ {nf.total_produtos:,.2f}")
    
    # Impostos declarados (totais da nota)
    icms_tot = root.find(".//nfe:ICMSTot", namespaces=ns)
    if icms_tot is not None:
        icms_val = _try_float(gx("nfe:vICMS", icms_tot))
        print(f"   📋 ICMS Declarado extraído do XML: R$ {icms_val:,.2f}")
        
        nf.declarados = Declarados(
            icms=icms_val,
            st=_try_float(gx("nfe:vST", icms_tot)),
            ipi=_try_float(gx("nfe:vIPI", icms_tot)),
            pis=_try_float(gx("nfe:vPIS", icms_tot)),
            cofins=_try_float(gx("nfe:vCOFINS", icms_tot)),
        )
    
    print(f"✅ XML: {len(itens)} itens extraídos")
    print(f"   Declarados: ICMS={nf.declarados.icms}, PIS={nf.declarados.pis}")
    return nf

def _parse_pdf(pdf_file: str) -> NotaFiscal:
    """Extrai dados completos do PDF"""
    import re
    
    try:
        import pdfplumber
    except:
        print("⚠️ pdfplumber não instalado!")
        return NotaFiscal()
    
    text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text += (page.extract_text() or "") + "\n"
    
    print(f"📄 PDF extraído: {len(text)} caracteres")
    print(f"🔍 PRIMEIROS 2000 CARACTERES DO PDF:")
    print("=" * 80)
    print(text[:2000])
    print("=" * 80)
    
    nf = NotaFiscal()
    
    # === CHAVE (44 dígitos seguidos) ===
    apenas_numeros = ''.join(c for c in text if c.isdigit())
    chave_match = re.search(r'(\d{44})', apenas_numeros)
    if chave_match:
        nf.chave = chave_match.group(1)
    
    # === NÚMERO ===
    num_patterns = [
        r'N[°º]\.\s*(\d{3}\.\d{3}\.\d{3})',
        r'NF-?e?\s*\s*N[°º]\.\s*(\d+)',
        r'N[úuÚU]mero\s*[:\-]?\s*(\d+)',
    ]
    for pattern in num_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            nf.numero = match.group(1).replace('.', '')
            break
    
    # === SÉRIE ===
    serie_match = re.search(r'S[ÉéE]RIE\s+(\d+)', text, re.IGNORECASE)
    if serie_match:
        nf.serie = serie_match.group(1)
    
    # === DATA ===
    data_match = re.search(r'(\d{2}[/-]\d{2}[/-]\d{4})', text)
    if data_match:
        nf.data_emissao = data_match.group(1)
    
    # === EMITENTE ===
    emitente_patterns = [
        r'Emitente[:\s]+.*?(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})',
        r'CNPJ[:\s]*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})',
    ]
    for pattern in emitente_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            nf.emitente_cnpj = match.group(1)
            break

    # Buscar "SJT COMERCIO DE VESTUARIO FEMININO LTDA"
    nome_emit_match = re.search(
        r'(?:RECEBEMOS DE|Emitente)\s+([A-ZÀ-Ú\s]+?)\s+(?:OS PRODUTOS|CNPJ)',
        text,
        re.IGNORECASE
    )
    if nome_emit_match:
        nf.emitente_nome = nome_emit_match.group(1).strip()
    
    # Fallback: pegar linha antes do CNPJ do emitente
    if not nf.emitente_nome and nf.emitente_cnpj:
        linhas_texto = text.split('\n')
        for idx, linha in enumerate(linhas_texto):
            if nf.emitente_cnpj in linha and idx > 0:
                nome_possivel = linhas_texto[idx-1].strip()
                if len(nome_possivel) > 5 and nome_possivel.replace(' ', '').isalpha():
                    nf.emitente_nome = nome_possivel
                    break
    
    # === DESTINATÁRIO (CPF ou CNPJ) ===
    # Buscar TODOS os CPFs do documento
    cpfs_formatados = re.findall(r'(\d{3}\.\d{3}\.\d{3}-\d{2})', text)
    
    # Pegar o SEGUNDO CPF (primeiro é emitente, segundo é destinatário)
    if len(cpfs_formatados) >= 2:
        nf.destinatario_cnpj = cpfs_formatados[1]
        print(f"   ✅ CPF Destinatário: {cpfs_formatados[1]}")
    elif len(cpfs_formatados) == 1:
        nf.destinatario_cnpj = cpfs_formatados[0]

    # === NOME DESTINATÁRIO ===
    nome_match = re.search(r'NOME/RAZÃO SOCIAL.*?\n\s*([A-ZÀ-Ú\s]+?)\s+\d{3}\.\d{3}\.\d{3}', text)
    if nome_match:
        nf.destinatario_nome = nome_match.group(1).strip()
    
    # === VALOR TOTAL - BUSCA DIRETA NA TABELA ===
    print("\n🔍 PROCURANDO VALOR TOTAL...")
    
    valor_total = 0
    linha_valor = re.search(r'VALOR\s+TOTAL\s+DA\s+NOTA.*\n.*', text, re.IGNORECASE)
    
    if linha_valor:
        # Pegar TODOS os valores da próxima linha
        valores_linha = re.findall(r'[\d\.]+,[\d]{2}', linha_valor.group(0))
        print(f"   📋 Valores encontrados: {valores_linha}")
        
        if valores_linha:
            # Pegar o ÚLTIMO valor (que é o total da nota)
            valor_str = valores_linha[-1].replace('.', '').replace(',', '.')
            valor_total = _try_float(valor_str)
            print(f"✅ Valor total: R$ {valor_total:,.2f}")

    # === IMPOSTOS DECLARADOS ===
    linha_impostos = re.search(
        r'BASE DE CÁLCULO DO ICMS\s+VALOR DO ICMS.*?\n\s*([\d,\.]+)\s+([\d,\.]+)',
        text,
        re.IGNORECASE
    )
    if linha_impostos:
        valor_icms = _try_float(linha_impostos.group(2).replace('.', '').replace(',', '.'))
        nf.declarados = Declarados(icms=valor_icms)
        print(f"   📋 ICMS Declarado: R$ {valor_icms:,.2f}")

    if not nf.itens and valor_total > 0:
        nf.itens = [Item(
            codigo="1",
            descricao="Produto/Serviço extraído do PDF",
            ncm="",
            cfop="5102",
            quantidade=1.0,
            valor_unitario=valor_total,
            valor_total=valor_total
        )]
    
    print(f"\n✅ PDF FINAL: {len(nf.itens)} itens | Valor: R$ {valor_total:,.2f}")
    print(f"   Chave: {nf.chave or 'N/A'}")
    print(f"   Número: {nf.numero or 'N/A'}")
    print(f"   CPF Dest: {nf.destinatario_cnpj or 'N/A'}")
    
    return nf

def _parse_image(img_file: str) -> NotaFiscal:
    """OCR completo para extrair dados da imagem"""
    import re
    
    if not _HAS_TESS:
        print("⚠️ pytesseract não instalado!")
        return NotaFiscal()
    
    try:
        img = Image.open(img_file).convert('L')  # Grayscale
        text = pytesseract.image_to_string(img, lang='por')
    except Exception as e:
        print(f"⚠️ Erro OCR: {e}")
        return NotaFiscal()
    
    print(f"🖼️ OCR extraído: {len(text)} caracteres")
    
    nf = NotaFiscal()
    
    # === CHAVE ===
    chave_patterns = [
        r'(\d{4}\s+\d{4}\s+\d{4}\s+\d{4}\s+\d{4}\s+\d{4}\s+\d{4}\s+\d{4}\s+\d{4}\s+\d{4}\s+\d{4})',
        r'\b(\d{44})\b'
    ]
    for pattern in chave_patterns:
        match = re.search(pattern, text)
        if match:
            nf.chave = match.group(1).replace(' ', '')
            break
    
    # === NÚMERO ===
    num_patterns = [
        r'N[úu]mero\s*[:\-]?\s*(\d+)',
        r'N[°º]\s*(\d+)',
    ]
    for pattern in num_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            nf.numero = match.group(1)
            break
    
    # === SÉRIE ===
    serie_match = re.search(r'S[ée]rie\s*[:\-]?\s*(\d+)', text, re.IGNORECASE)
    if serie_match:
        nf.serie = serie_match.group(1)
    
    # === DATA ===
    data_match = re.search(r'(\d{2}[/-]\d{2}[/-]\d{4})', text)
    if data_match:
        nf.data_emissao = data_match.group(1)
    
    # === CNPJs ===
    cnpjs = re.findall(r'(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})', text)
    if not cnpjs:
        cnpjs = re.findall(r'\b(\d{14})\b', text)
    
    if len(cnpjs) >= 2:
        nf.emitente_cnpj = cnpjs[0]
        nf.destinatario_cnpj = cnpjs[1]
    elif len(cnpjs) == 1:
        nf.emitente_cnpj = cnpjs[0]
    
    # === EXTRAIR ITEM COM VALOR ===
    valor_patterns = [
        r'Valor\s+Total\s*[:\-]?\s*R?\$?\s*([\d\.,]+)',
        r'VALOR\s+TOTAL\s*[:\-]?\s*R?\$?\s*([\d\.,]+)',
        r'V\.\s*TOTAL\s*[:\-]?\s*R?\$?\s*([\d\.,]+)',
    ]
    
    for pattern in valor_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            valor_str = match.group(1).replace('.', '').replace(',', '.')
            valor_total = _try_float(valor_str)
            
            if valor_total > 0:
                nf.itens = [Item(
                    codigo="1",
                    descricao="Produto/Serviço extraído via OCR",
                    ncm="",
                    cfop="5102",
                    quantidade=1.0,
                    valor_unitario=valor_total,
                    valor_total=valor_total
                )]
                break
    
    # === IMPOSTOS DECLARADOS (se houver) ===
    impostos = {}
    impostos_regex = {
        'icms': r'ICMS\s*[:\-]?\s*R?\$?\s*([\d\.,]+)',
        'pis': r'PIS\s*[:\-]?\s*R?\$?\s*([\d\.,]+)',
        'cofins': r'COFINS\s*[:\-]?\s*R?\$?\s*([\d\.,]+)',
    }
    
    for imp, regex in impostos_regex.items():
        match = re.search(regex, text, re.IGNORECASE)
        if match:
            valor_str = match.group(1).replace('.', '').replace(',', '.')
            impostos[imp] = _try_float(valor_str)
    
    if impostos:
        nf.declarados = Declarados(**impostos)
    
    print(f"✅ Imagem: {len(nf.itens)} itens | Chave: {nf.chave or 'N/A'}")
    
    return nf

def parse_any(nf_csv_file=None, xml_file=None, pdf_file=None, image_file=None):
    import os

    # =========================
    # 1) CSV ÚNICO
    # =========================
    if isinstance(nf_csv_file, str) and os.path.exists(nf_csv_file):
        return _parse_csv_any(nf_csv_file)

    # =========================
    # 2) LISTA DE CSV (CAB + ITENS)
    # =========================
    if isinstance(nf_csv_file, list):
        cab = None
        itm = None

        for f in nf_csv_file:
            if not f or not os.path.exists(f):
                continue
            name = os.path.basename(f).lower()
            if "item" in name or "itens" in name:
                itm = f
            else:
                cab = f

        # CAB + ITENS → monta NF e substitui itens
        if cab and itm:
            nf = _parse_csv_any(cab)

            cfg = _sniff_csv(itm)
            df_itm = pd.read_csv(itm, encoding=cfg["encoding"], sep=cfg["sep"], engine="python")

            c = {c.strip().upper(): c for c in df_itm.columns}
            def C(*names):
                for n in names:
                    if n in c: return c[n]
                return None

            itens = []
            for _, r in df_itm.iterrows():
                itens.append(Item(
                    codigo=str(r.get(C("NÚMERO PRODUTO","CODIGO","CÓDIGO","COD"), "")),
                    descricao=str(r.get(C("DESCRIÇÃO DO PRODUTO/SERVIÇO","DESCRICAO"), "")),
                    ncm=str(r.get(C("CÓDIGO NCM/SH","NCM","NCM/SH (TIPO DE PRODUTO)"), "")),
                    cfop=str(r.get(C("CFOP"), "")),
                    quantidade=_try_float(r.get(C("QUANTIDADE","QTD","QCOM"), 0)),
                    valor_unitario=_try_float(r.get(C("VALOR UNITÁRIO","VUNCOM"), 0)),
                    valor_total=_try_float(r.get(C("VALOR TOTAL","VPROD"), 0)),
                ))

            nf.itens = itens
            return nf

        # Se só um existe
        if cab:
            return _parse_csv_any(cab)
        if itm:
            return _parse_csv_any(itm)

    # =========================
    # 3) XML
    # =========================
    if xml_file and os.path.exists(xml_file):
        return _parse_xml(xml_file)

    # =========================
    # 4) PDF
    # =========================
    if pdf_file and os.path.exists(pdf_file):
        return _parse_pdf(pdf_file)

    # =========================
    # 5) IMAGEM
    # =========================
    if image_file and os.path.exists(image_file):
        return _parse_image(image_file)

    raise FileNotFoundError("Nenhuma fonte válida encontrada (CSV/XML/PDF/Imagem).")

# ==========================================================
# COMPATIBILIDADE COM PIPELINE ANTIGO (NÃO ALTERAR LÓGICA)
# ==========================================================

def parse_csv(path: str):
    """
    Wrapper compatível com o pipeline.
    Usa o parser atual.
    """
    return _parse_csv_any(path)


def parse_csv_pares(cab: str, itm: str):
    """
    Wrapper compatível para caso CSV Cabeçalho + CSV Itens.
    Reaproveita o parse do cabeçalho e substitui itens.
    """
    nf = _parse_csv_any(cab)

    cfg = _sniff_csv(itm)
    df_itm = pd.read_csv(itm, encoding=cfg["encoding"], sep=cfg["sep"], engine="python")

    c = {c.strip().upper(): c for c in df_itm.columns}
    def C(*names):
        for n in names:
            if n in c: return c[n]
        return None

    itens = []
    for _, r in df_itm.iterrows():
        itens.append(Item(
            codigo=str(r.get(C("NÚMERO PRODUTO","CODIGO","CÓDIGO","COD"), "")),
            descricao=str(r.get(C("DESCRIÇÃO DO PRODUTO/SERVIÇO","DESCRICAO"), "")),
            ncm=str(r.get(C("CÓDIGO NCM/SH","NCM","NCM/SH (TIPO DE PRODUTO)"), "")),
            cfop=str(r.get(C("CFOP"), "")),
            quantidade=_try_float(r.get(C("QUANTIDADE","QTD","QCOM"), 0)),
            valor_unitario=_try_float(r.get(C("VALOR UNITÁRIO","VUNCOM"), 0)),
            valor_total=_try_float(r.get(C("VALOR TOTAL","VPROD"), 0)),
        ))

    nf.itens = itens
    return nf