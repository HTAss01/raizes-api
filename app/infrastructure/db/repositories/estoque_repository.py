"""Acesso a dados de estoque.

A operação crítica é `obter_com_lock`: o saldo da unidade/produto é lido
com FOR UPDATE antes de qualquer alteração, para que duas requisições
simultâneas (Totem e App, por exemplo) não vendam a mesma unidade. No
SQLite o lock é ignorado pelo engine, mas a transação curta mantém a
consistência; no PostgreSQL ele é efetivo.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.db.models import Estoque, Produto


def obter(db: Session, unidade_id: int, produto_id: int, *, lock: bool = False) -> Estoque | None:
    stmt = select(Estoque).where(
        Estoque.unidade_id == unidade_id,
        Estoque.produto_id == produto_id,
    )
    if lock:
        stmt = stmt.with_for_update()
    return db.scalar(stmt)


def listar_por_unidade(db: Session, unidade_id: int) -> list[tuple[Estoque, Produto]]:
    stmt = (
        select(Estoque, Produto)
        .join(Produto, Produto.id == Estoque.produto_id)
        .where(Estoque.unidade_id == unidade_id)
        .order_by(Produto.nome)
    )
    return list(db.execute(stmt).tuples())


def reservar(estoque: Estoque, quantidade: int) -> None:
    estoque.quantidade_reservada += quantidade


def liberar(estoque: Estoque, quantidade: int) -> None:
    estoque.quantidade_reservada = max(0, estoque.quantidade_reservada - quantidade)


def baixar(estoque: Estoque, quantidade: int) -> None:
    """Converte reserva em saída física do estoque."""

    estoque.quantidade_reservada = max(0, estoque.quantidade_reservada - quantidade)
    estoque.quantidade = max(0, estoque.quantidade - quantidade)
