"""Acesso a dados de pedidos."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.domain.enums import CanalPedido, StatusPedido
from app.infrastructure.db.models import Pedido, PedidoItem


def obter(db: Session, pedido_id: int, *, lock: bool = False) -> Pedido | None:
    stmt = select(Pedido).where(Pedido.id == pedido_id)
    if lock:
        stmt = stmt.with_for_update()
    return db.scalar(stmt)


def obter_detalhado(db: Session, pedido_id: int) -> Pedido | None:
    stmt = (
        select(Pedido)
        .where(Pedido.id == pedido_id)
        .options(
            selectinload(Pedido.itens).selectinload(PedidoItem.produto),
            selectinload(Pedido.pagamentos),
            selectinload(Pedido.historico),
        )
    )
    return db.scalar(stmt)


def listar(
    db: Session,
    *,
    offset: int,
    limit: int,
    canal_pedido: CanalPedido | None = None,
    status: StatusPedido | None = None,
    unidade_id: int | None = None,
    cliente_id: int | None = None,
) -> tuple[list[Pedido], int]:
    stmt = select(Pedido).options(
        selectinload(Pedido.itens).selectinload(PedidoItem.produto)
    )
    if canal_pedido is not None:
        stmt = stmt.where(Pedido.canal_pedido == canal_pedido)
    if status is not None:
        stmt = stmt.where(Pedido.status == status)
    if unidade_id is not None:
        stmt = stmt.where(Pedido.unidade_id == unidade_id)
    if cliente_id is not None:
        stmt = stmt.where(Pedido.cliente_id == cliente_id)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    itens = list(
        db.scalars(stmt.order_by(Pedido.criado_em.desc(), Pedido.id.desc()).offset(offset).limit(limit))
    )
    return itens, total
