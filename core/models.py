# validador_fiscal/core/models.py
from typing import List, Optional
from pydantic import BaseModel, Field

class Item(BaseModel):
    codigo: Optional[str] = None
    descricao: Optional[str] = None
    ncm: Optional[str] = None
    cfop: Optional[str] = None
    subitem_lc116: Optional[str] = None
    quantidade: float = 1.0
    valor_unitario: float = 0.0
    valor_total: float = 0.0

class Declarados(BaseModel):
    icms: Optional[float] = None
    st: Optional[float] = None
    difal: Optional[float] = None
    ipi: Optional[float] = None
    pis: Optional[float] = None
    cofins: Optional[float] = None
    iss: Optional[float] = None
    irpj: Optional[float] = None
    csll: Optional[float] = None
    cbs: Optional[float] = None
    ibs: Optional[float] = None
    is_: Optional[float] = Field(default=None, alias="is")

class Calculados(BaseModel):
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

class NotaFiscal(BaseModel):
    id: Optional[int] = None
    chave: Optional[str] = None
    numero: Optional[str] = None
    serie: Optional[str] = None

    emitente_cnpj: Optional[str] = None
    emitente_nome: Optional[str] = None
    
    destinatario_cnpj: Optional[str] = None
    destinatario_cpf: Optional[str] = None  # ← CPF ADICIONADO
    destinatario_nome: Optional[str] = None
    
    emissor_uf: Optional[str] = None  # ← CORRIGIDO
    destinatario_uf: Optional[str] = None  # ← CORRIGIDO

    municipio_servico: Optional[str] = None
    uf_servico: Optional[str] = None

    data_emissao: Optional[str] = None
    total_produtos: float = 0.0  # Soma dos produtos
    total_nf: float = 0.0  # Valor final da nota

    itens: List[Item] = []
    declarados: Optional[Declarados] = None
    calculados: Optional[Calculados] = None