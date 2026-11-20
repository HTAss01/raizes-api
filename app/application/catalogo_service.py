"""Casos de uso de catálogo: unidades, produtos e cardápio por unidade."""

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.application.auditoria import registrar_auditoria
from app.domain.exceptions import RecursoNaoEncontradoError
from app.infrastructure.db.models import CardapioUnidade, Estoque, Produto, Unidade


def _total(db: Session, stmt) -> int:
    return db.scalar(select(func.count()).select_from(stmt.subquery())) or 0


def listar_unidades(
    db: Session, *, offset: int, limit: int, apenas_ativas: bool = True
) -> tuple[list[Unidade], int]:
    stmt = select(Unidade)
    if apenas_ativas:
        stmt = stmt.where(Unidade.ativo.is_(True))
    total = _total(db, stmt)
    itens = list(db.scalars(stmt.order_by(Unidade.nome).offset(offset).limit(limit)))
    return itens, total


def obter_unidade(db: Session, unidade_id: int, *, exigir_ativa: bool = True) -> Unidade:
    unidade = db.get(Unidade, unidade_id)
    if unidade is None or (exigir_ativa and not unidade.ativo):
        raise RecursoNaoEncontradoError("Unidade não encontrada.")
    return unidade


def criar_unidade(
    db: Session, dados: dict, *, usuario_id: int | None, request_id: str | None
) -> Unidade:
    unidade = Unidade(**dados)
    db.add(unidade)
    db.flush()
    registrar_auditoria(
        db,
        acao="UNIDADE_CRIADA",
        entidade="unidades",
        entidade_id=unidade.id,
        usuario_id=usuario_id,
        dados_novos={"nome": unidade.nome, "cidade": unidade.cidade, "uf": unidade.uf},
        request_id=request_id,
    )
    db.commit()
    db.refresh(unidade)
    return unidade


def listar_produtos(
    db: Session,
    *,
    offset: int,
    limit: int,
    categoria: str | None = None,
    ativo: bool | None = None,
    busca: str | None = None,
) -> tuple[list[Produto], int]:
    stmt = select(Produto)
    if categoria:
        stmt = stmt.where(func.upper(Produto.categoria) == categoria.upper())
    if ativo is not None:
        stmt = stmt.where(Produto.ativo.is_(ativo))
    if busca:
        stmt = stmt.where(Produto.nome.ilike(f"%{busca}%"))
    total = _total(db, stmt)
    itens = list(db.scalars(stmt.order_by(Produto.nome).offset(offset).limit(limit)))
    return itens, total


def obter_produto(db: Session, produto_id: int) -> Produto:
    produto = db.get(Produto, produto_id)
    if produto is None:
        raise RecursoNaoEncontradoError("Produto não encontrado.")
    return produto


def criar_produto(
    db: Session, dados: dict, *, usuario_id: int | None, request_id: str | None
) -> Produto:
    """Cria o produto e já o habilita nas unidades ativas (preço base, saldo 0)."""

    produto = Produto(**dados)
    db.add(produto)
    db.flush()

    for unidade_id in db.scalars(select(Unidade.id).where(Unidade.ativo.is_(True))):
        db.add(
            CardapioUnidade(
                unidade_id=unidade_id,
                produto_id=produto.id,
                preco=produto.preco_base,
                disponivel=True,
            )
        )
        db.add(
            Estoque(
                unidade_id=unidade_id,
                produto_id=produto.id,
                quantidade=0,
                quantidade_reservada=0,
                estoque_minimo=0,
            )
        )

    registrar_auditoria(
        db,
        acao="PRODUTO_CRIADO",
        entidade="produtos",
        entidade_id=produto.id,
        usuario_id=usuario_id,
        dados_novos={"nome": produto.nome, "precoBase": str(produto.preco_base)},
        request_id=request_id,
    )
    db.commit()
    db.refresh(produto)
    return produto


def atualizar_produto(
    db: Session,
    produto_id: int,
    dados: dict,
    *,
    usuario_id: int | None,
    request_id: str | None,
) -> Produto:
    produto = obter_produto(db, produto_id)
    anteriores = {
        "nome": produto.nome,
        "categoria": produto.categoria,
        "precoBase": str(produto.preco_base),
        "ativo": produto.ativo,
    }
    for campo, valor in dados.items():
        setattr(produto, campo, valor)

    registrar_auditoria(
        db,
        acao="PRODUTO_ATUALIZADO",
        entidade="produtos",
        entidade_id=produto.id,
        usuario_id=usuario_id,
        dados_anteriores=anteriores,
        dados_novos={k: str(v) for k, v in dados.items()},
        request_id=request_id,
    )
    db.commit()
    db.refresh(produto)
    return produto


def desativar_produto(
    db: Session, produto_id: int, *, usuario_id: int | None, request_id: str | None
) -> None:
    """Desativação lógica: preserva o histórico de pedidos e movimentações."""

    produto = obter_produto(db, produto_id)
    produto.ativo = False
    registrar_auditoria(
        db,
        acao="PRODUTO_DESATIVADO",
        entidade="produtos",
        entidade_id=produto.id,
        usuario_id=usuario_id,
        dados_anteriores={"ativo": True},
        dados_novos={"ativo": False},
        request_id=request_id,
    )
    db.commit()


def listar_cardapio(
    db: Session,
    unidade_id: int,
    *,
    categoria: str | None = None,
    apenas_disponiveis: bool = False,
    offset: int = 0,
    limit: int | None = None,
) -> tuple[list[dict], int]:
    obter_unidade(db, unidade_id)

    stmt = (
        select(CardapioUnidade, Produto, Estoque)
        .join(Produto, Produto.id == CardapioUnidade.produto_id)
        .outerjoin(
            Estoque,
            (Estoque.produto_id == CardapioUnidade.produto_id)
            & (Estoque.unidade_id == CardapioUnidade.unidade_id),
        )
        .where(CardapioUnidade.unidade_id == unidade_id, Produto.ativo.is_(True))
        .order_by(Produto.nome)
    )
    if categoria:
        stmt = stmt.where(func.upper(Produto.categoria) == categoria.upper())

    itens = []
    for cardapio, produto, estoque in db.execute(stmt).tuples():
        disponivel = bool(cardapio.disponivel) and (estoque is None or estoque.disponivel > 0)
        if apenas_disponiveis and not disponivel:
            continue
        itens.append(
            {
                "produto_id": produto.id,
                "nome": produto.nome,
                "categoria": produto.categoria,
                "preco": cardapio.preco,
                "disponivel": disponivel,
                "estoque_disponivel": estoque.disponivel if estoque else 0,
            }
        )

    total = len(itens)
    if limit is not None:
        itens = itens[offset : offset + limit]
    return itens, total


def definir_item_cardapio(
    db: Session,
    unidade_id: int,
    produto_id: int,
    *,
    preco: Decimal | None,
    disponivel: bool | None,
    usuario_id: int | None,
    request_id: str | None,
) -> CardapioUnidade:
    obter_unidade(db, unidade_id)
    produto = obter_produto(db, produto_id)

    item = db.scalar(
        select(CardapioUnidade).where(
            CardapioUnidade.unidade_id == unidade_id,
            CardapioUnidade.produto_id == produto_id,
        )
    )
    if item is None:
        item = CardapioUnidade(
            unidade_id=unidade_id,
            produto_id=produto_id,
            preco=preco if preco is not None else produto.preco_base,
            disponivel=True if disponivel is None else disponivel,
        )
        db.add(item)
    else:
        if preco is not None:
            item.preco = preco
        if disponivel is not None:
            item.disponivel = disponivel

    db.flush()
    registrar_auditoria(
        db,
        acao="CARDAPIO_ATUALIZADO",
        entidade="cardapio_unidade",
        entidade_id=f"{unidade_id}:{produto_id}",
        usuario_id=usuario_id,
        dados_novos={"preco": str(item.preco), "disponivel": item.disponivel},
        request_id=request_id,
    )
    db.commit()
    db.refresh(item)
    return item
