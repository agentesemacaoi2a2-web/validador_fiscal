# validador_fiscal/db/models.py
# Modelo ORM (SQLAlchemy) - versão compatível e não duplicada com core.models (Pydantic).
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship
from .base import Base

class NotaFiscal(Base):
    __tablename__ = "nota_fiscal"
    id = Column(Integer, primary_key=True, index=True)

    chave = Column(String(64), nullable=True, index=True)
    numero = Column(String(32), nullable=True, index=True)
    serie = Column(String(16), nullable=True)

    emitente_cnpj = Column(String(20), nullable=True, index=True)
    emitente_nome = Column(String(255), nullable=True)
    destinatario_cnpj = Column(String(20), nullable=True, index=True)
    destinatario_nome = Column(String(255), nullable=True)

    uf_origem = Column(String(2), nullable=True)
    uf_destino = Column(String(2), nullable=True)

    municipio_servico = Column(String(100), nullable=True)
    uf_servico = Column(String(2), nullable=True)

    data_emissao = Column(String(32), nullable=True)
    total_nf = Column(Float, default=0.0)

    itens = relationship("NotaFiscalItem", back_populates="nf", cascade="all, delete-orphan")
    declarados = relationship("ImpostoDeclarado", back_populates="nf", cascade="all, delete-orphan")
    calculados = relationship("ImpostoCalculado", back_populates="nf", cascade="all, delete-orphan")
    divergencias = relationship("Divergencia", back_populates="nf", cascade="all, delete-orphan")
    etapas = relationship("Etapa", back_populates="nf", cascade="all, delete-orphan")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class NotaFiscalItem(Base):
    __tablename__ = "nota_fiscal_item"
    id = Column(Integer, primary_key=True, index=True)
    nota_id = Column(Integer, ForeignKey("nota_fiscal.id"), index=True)

    codigo = Column(String(80), nullable=True)
    descricao = Column(Text, nullable=True)
    ncm = Column(String(20), nullable=True)
    cfop = Column(String(10), nullable=True)
    subitem_lc116 = Column(String(10), nullable=True)

    municipio_servico = Column(String(100), nullable=True)
    uf_servico = Column(String(2), nullable=True)

    quantidade = Column(Float, default=1.0)
    valor_unitario = Column(Float, default=0.0)
    valor_total = Column(Float, default=0.0)

    nf = relationship("NotaFiscal", back_populates="itens")

class ImpostoDeclarado(Base):
    __tablename__ = "imposto_declarado"
    id = Column(Integer, primary_key=True, index=True)
    nota_id = Column(Integer, ForeignKey("nota_fiscal.id"), index=True)
    imposto = Column(String(20), index=True)
    valor = Column(Float, default=0.0)
    nf = relationship("NotaFiscal", back_populates="declarados")
    __table_args__ = (Index("ix_decl_nf_imposto", "nota_id", "imposto"),)

class ImpostoCalculado(Base):
    __tablename__ = "imposto_calculado"
    id = Column(Integer, primary_key=True, index=True)
    nota_id = Column(Integer, ForeignKey("nota_fiscal.id"), index=True)
    imposto = Column(String(20), index=True)
    base = Column(Float, default=0.0)
    aliquota = Column(Float, default=0.0)
    valor = Column(Float, default=0.0)
    fonte = Column(String(40), default="LEGADO")
    item_idx = Column(Integer, default=-1)
    nf = relationship("NotaFiscal", back_populates="calculados")
    __table_args__ = (Index("ix_calc_nf_imposto", "nota_id", "imposto"),)

class Divergencia(Base):
    __tablename__ = "divergencia"
    id = Column(Integer, primary_key=True, index=True)
    nota_id = Column(Integer, ForeignKey("nota_fiscal.id"), index=True)
    imposto = Column(String(20), index=True)
    tipo = Column(String(20))
    mensagem = Column(Text)
    valor_decl = Column(Float, default=0.0)
    valor_calc = Column(Float, default=0.0)
    nf = relationship("NotaFiscal", back_populates="divergencias")

class Etapa(Base):
    __tablename__ = "etapa"
    id = Column(Integer, primary_key=True, index=True)
    nota_id = Column(Integer, ForeignKey("nota_fiscal.id"), index=True)
    etapa = Column(String(60), index=True)
    ts = Column(String(32), index=True)
    nf = relationship("NotaFiscal", back_populates="etapas")

class Relatorio(Base):
    __tablename__ = "relatorio"
    id = Column(Integer, primary_key=True, index=True)
    nota_id = Column(Integer, ForeignKey("nota_fiscal.id"), index=True)
    session_id = Column(String(60), index=True)
    json_path = Column(String(512), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    nf = relationship("NotaFiscal")

class ChatMessageDB(Base):
    __tablename__ = "chat_message"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(60), index=True)
    role = Column(String(10))
    content = Column(Text)
    ts = Column(String(32), index=True)
    __table_args__ = (Index("ix_chat_session_order", "session_id", "id"),)
