"""Modelos ORM (SQLAlchemy 2.0) - 14 entidades do DER.

Convenções:
- Nomes de tabela/coluna em português, coerentes com o DER entregue.
- Dinheiro em Numeric(10, 2); nunca float.
- Enum persistido como VARCHAR + CHECK (native_enum=False) para portabilidade
  entre SQLite e PostgreSQL.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import (
    CanalPedido,
    FormaPagamento,
    PerfilUsuario,
    StatusPagamento,
    StatusPedido,
    TipoDescontoPromocao,
    TipoMovimentacaoEstoque,
    TipoTransacaoPontos,
)
from app.infrastructure.db.base import Base, utcnow

ENUM_LEN = 30


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(180), nullable=False, unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    perfil: Mapped[PerfilUsuario] = mapped_column(
        SAEnum(PerfilUsuario, native_enum=False, length=ENUM_LEN), nullable=False
    )
    telefone: Mapped[str | None] = mapped_column(String(20))
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    consentimento_lgpd: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    consentimento_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    pedidos: Mapped[list["Pedido"]] = relationship(back_populates="cliente")
    pontos: Mapped[list["PontoTransacao"]] = relationship(back_populates="cliente")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan"
    )


class Unidade(Base):
    __tablename__ = "unidades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    cidade: Mapped[str] = mapped_column(String(80), nullable=False)
    uf: Mapped[str] = mapped_column(String(2), nullable=False)
    endereco: Mapped[str] = mapped_column(String(200), nullable=False)
    telefone: Mapped[str | None] = mapped_column(String(20))
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    cardapio: Mapped[list["CardapioUnidade"]] = relationship(
        back_populates="unidade", cascade="all, delete-orphan"
    )
    estoques: Mapped[list["Estoque"]] = relationship(
        back_populates="unidade", cascade="all, delete-orphan"
    )
    pedidos: Mapped[list["Pedido"]] = relationship(back_populates="unidade")


class Produto(Base):
    __tablename__ = "produtos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text)
    categoria: Mapped[str] = mapped_column(String(60), nullable=False)
    preco_base: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (CheckConstraint("preco_base >= 0", name="preco_base_positivo"),)

    cardapio: Mapped[list["CardapioUnidade"]] = relationship(
        back_populates="produto", cascade="all, delete-orphan"
    )
    estoques: Mapped[list["Estoque"]] = relationship(
        back_populates="produto", cascade="all, delete-orphan"
    )


class CardapioUnidade(Base):
    """Cardápio por unidade: preço e disponibilidade próprios de cada loja."""

    __tablename__ = "cardapio_unidade"
    __table_args__ = (
        UniqueConstraint("unidade_id", "produto_id", name="unidade_produto"),
        CheckConstraint("preco >= 0", name="preco_positivo"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    unidade_id: Mapped[int] = mapped_column(ForeignKey("unidades.id", ondelete="CASCADE"), nullable=False)
    produto_id: Mapped[int] = mapped_column(ForeignKey("produtos.id", ondelete="CASCADE"), nullable=False)
    preco: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    disponivel: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    unidade: Mapped[Unidade] = relationship(back_populates="cardapio")
    produto: Mapped[Produto] = relationship(back_populates="cardapio")


class Estoque(Base):
    """Saldo de estoque por unidade (uma unidade possui estoque próprio)."""

    __tablename__ = "estoques"
    __table_args__ = (
        UniqueConstraint("unidade_id", "produto_id", name="unidade_produto"),
        CheckConstraint("quantidade >= 0", name="quantidade_nao_negativa"),
        CheckConstraint("quantidade_reservada >= 0", name="reservada_nao_negativa"),
        CheckConstraint("quantidade_reservada <= quantidade", name="reserva_menor_que_saldo"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    unidade_id: Mapped[int] = mapped_column(ForeignKey("unidades.id", ondelete="CASCADE"), nullable=False)
    produto_id: Mapped[int] = mapped_column(ForeignKey("produtos.id", ondelete="CASCADE"), nullable=False)
    quantidade: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quantidade_reservada: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estoque_minimo: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    unidade: Mapped[Unidade] = relationship(back_populates="estoques")
    produto: Mapped[Produto] = relationship(back_populates="estoques")

    @property
    def disponivel(self) -> int:
        return self.quantidade - self.quantidade_reservada


class MovimentacaoEstoque(Base):
    """Histórico append-only de entradas, saídas, reservas e baixas."""

    __tablename__ = "movimentacoes_estoque"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    unidade_id: Mapped[int] = mapped_column(ForeignKey("unidades.id"), nullable=False)
    produto_id: Mapped[int] = mapped_column(ForeignKey("produtos.id"), nullable=False)
    tipo: Mapped[TipoMovimentacaoEstoque] = mapped_column(
        SAEnum(TipoMovimentacaoEstoque, native_enum=False, length=ENUM_LEN), nullable=False
    )
    quantidade: Mapped[int] = mapped_column(Integer, nullable=False)
    motivo: Mapped[str | None] = mapped_column(String(200))
    pedido_id: Mapped[int | None] = mapped_column(ForeignKey("pedidos.id"))
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        CheckConstraint("quantidade > 0", name="quantidade_positiva"),
        Index("ix_movimentacoes_estoque_unidade_produto", "unidade_id", "produto_id"),
    )


class Pedido(Base):
    """Pedido multicanal - canalPedido é obrigatório por regra de negócio."""

    __tablename__ = "pedidos"
    __table_args__ = (CheckConstraint("total >= 0", name="total_nao_negativo"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cliente_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    unidade_id: Mapped[int] = mapped_column(ForeignKey("unidades.id"), nullable=False)
    canal_pedido: Mapped[CanalPedido] = mapped_column(
        SAEnum(CanalPedido, native_enum=False, length=ENUM_LEN), nullable=False, index=True
    )
    status: Mapped[StatusPedido] = mapped_column(
        SAEnum(StatusPedido, native_enum=False, length=ENUM_LEN),
        nullable=False,
        default=StatusPedido.AGUARDANDO_PAGAMENTO,
        index=True,
    )
    forma_pagamento: Mapped[FormaPagamento] = mapped_column(
        SAEnum(FormaPagamento, native_enum=False, length=ENUM_LEN), nullable=False
    )
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    observacao: Mapped[str | None] = mapped_column(String(255))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    cliente: Mapped[Usuario | None] = relationship(back_populates="pedidos")
    unidade: Mapped[Unidade] = relationship(back_populates="pedidos")
    itens: Mapped[list["PedidoItem"]] = relationship(
        back_populates="pedido", cascade="all, delete-orphan", order_by="PedidoItem.id"
    )
    pagamentos: Mapped[list["Pagamento"]] = relationship(
        back_populates="pedido", cascade="all, delete-orphan", order_by="Pagamento.id"
    )
    historico: Mapped[list["PedidoStatusHistorico"]] = relationship(
        back_populates="pedido", cascade="all, delete-orphan", order_by="PedidoStatusHistorico.id"
    )


class PedidoItem(Base):
    """Preço unitário congela o valor do cardápio no momento do pedido."""

    __tablename__ = "pedido_itens"
    __table_args__ = (
        CheckConstraint("quantidade > 0", name="quantidade_positiva"),
        CheckConstraint("preco_unitario >= 0", name="preco_unitario_positivo"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pedido_id: Mapped[int] = mapped_column(ForeignKey("pedidos.id", ondelete="CASCADE"), nullable=False)
    produto_id: Mapped[int] = mapped_column(ForeignKey("produtos.id"), nullable=False)
    quantidade: Mapped[int] = mapped_column(Integer, nullable=False)
    preco_unitario: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    pedido: Mapped[Pedido] = relationship(back_populates="itens")
    produto: Mapped[Produto] = relationship()


class Pagamento(Base):
    """Pagamento desacoplado do pedido, com chave de idempotência."""

    __tablename__ = "pagamentos"
    __table_args__ = (
        CheckConstraint("valor >= 0", name="valor_nao_negativo"),
        Index("ix_pagamentos_pedido_status", "pedido_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pedido_id: Mapped[int] = mapped_column(ForeignKey("pedidos.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[StatusPagamento] = mapped_column(
        SAEnum(StatusPagamento, native_enum=False, length=ENUM_LEN),
        nullable=False,
        default=StatusPagamento.PENDENTE,
    )
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    forma_pagamento: Mapped[FormaPagamento] = mapped_column(
        SAEnum(FormaPagamento, native_enum=False, length=ENUM_LEN), nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    transacao_externa_id: Mapped[str | None] = mapped_column(String(120))
    motivo_recusa: Mapped[str | None] = mapped_column(String(255))
    payload_resposta: Mapped[dict | None] = mapped_column(JSON)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    processado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    pedido: Mapped[Pedido] = relationship(back_populates="pagamentos")


class PontoTransacao(Base):
    """Extrato de fidelidade. Um crédito por pedido (constraint garante)."""

    __tablename__ = "pontos_transacoes"
    __table_args__ = (
        UniqueConstraint("pedido_id", "tipo", name="pedido_tipo"),
        CheckConstraint("pontos > 0", name="pontos_positivos"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False, index=True)
    pedido_id: Mapped[int | None] = mapped_column(ForeignKey("pedidos.id"))
    tipo: Mapped[TipoTransacaoPontos] = mapped_column(
        SAEnum(TipoTransacaoPontos, native_enum=False, length=ENUM_LEN), nullable=False
    )
    pontos: Mapped[int] = mapped_column(Integer, nullable=False)
    descricao: Mapped[str] = mapped_column(String(200), nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    cliente: Mapped[Usuario] = relationship(back_populates="pontos")


class Promocao(Base):
    """Promoção/campanha: global (sem unidade/produto) ou escopada."""

    __tablename__ = "promocoes"
    __table_args__ = (CheckConstraint("valor > 0", name="valor_positivo"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    descricao: Mapped[str | None] = mapped_column(String(255))
    tipo_desconto: Mapped[TipoDescontoPromocao] = mapped_column(
        SAEnum(TipoDescontoPromocao, native_enum=False, length=ENUM_LEN), nullable=False
    )
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    unidade_id: Mapped[int | None] = mapped_column(ForeignKey("unidades.id"))
    produto_id: Mapped[int | None] = mapped_column(ForeignKey("produtos.id"))
    data_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    data_fim: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class PedidoStatusHistorico(Base):
    """Trilha de auditoria da máquina de estados do pedido."""

    __tablename__ = "pedido_status_historico"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pedido_id: Mapped[int] = mapped_column(ForeignKey("pedidos.id", ondelete="CASCADE"), nullable=False, index=True)
    status_anterior: Mapped[StatusPedido | None] = mapped_column(
        SAEnum(StatusPedido, native_enum=False, length=ENUM_LEN)
    )
    status_novo: Mapped[StatusPedido] = mapped_column(
        SAEnum(StatusPedido, native_enum=False, length=ENUM_LEN), nullable=False
    )
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    observacao: Mapped[str | None] = mapped_column(String(255))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    pedido: Mapped[Pedido] = relationship(back_populates="historico")


class LogAuditoria(Base):
    """Log append-only de ações sensíveis (LGPD / rastreabilidade)."""

    __tablename__ = "auditoria_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), index=True)
    acao: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    entidade: Mapped[str] = mapped_column(String(60), nullable=False)
    entidade_id: Mapped[str | None] = mapped_column(String(60))
    dados_anteriores: Mapped[dict | None] = mapped_column(JSON)
    dados_novos: Mapped[dict | None] = mapped_column(JSON)
    request_id: Mapped[str | None] = mapped_column(String(64), index=True)
    ip: Mapped[str | None] = mapped_column(String(45))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)


class RefreshToken(Base):
    """Refresh token persistido apenas como hash."""

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revogado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    usuario: Mapped[Usuario] = relationship(back_populates="refresh_tokens")
