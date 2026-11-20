"""Casos de uso de estoque por unidade."""

from sqlalchemy.orm import Session

from app.application import catalogo_service
from app.application.auditoria import registrar_auditoria
from app.domain.enums import TipoMovimentacaoEstoque
from app.domain.exceptions import EstoqueInsuficienteError, RecursoNaoEncontradoError
from app.infrastructure.db.models import MovimentacaoEstoque, Usuario
from app.infrastructure.db.repositories import estoque_repository


def listar_estoque(
    db: Session, unidade_id: int, *, offset: int = 0, limit: int | None = None
) -> tuple[list[dict], int]:
    catalogo_service.obter_unidade(db, unidade_id)
    registros = estoque_repository.listar_por_unidade(db, unidade_id)
    itens = [
        {
            "produto_id": produto.id,
            "nome": produto.nome,
            "categoria": produto.categoria,
            "quantidade": estoque.quantidade,
            "quantidade_reservada": estoque.quantidade_reservada,
            "disponivel": estoque.disponivel,
            "estoque_minimo": estoque.estoque_minimo,
            "abaixo_do_minimo": estoque.quantidade < estoque.estoque_minimo,
        }
        for estoque, produto in registros
    ]
    total = len(itens)
    if limit is not None:
        itens = itens[offset : offset + limit]
    return itens, total


def movimentar(
    db: Session,
    *,
    unidade_id: int,
    produto_id: int,
    tipo: TipoMovimentacaoEstoque,
    quantidade: int,
    motivo: str | None,
    usuario: Usuario | None,
    request_id: str | None,
) -> tuple[MovimentacaoEstoque, int, int]:
    """Lança entrada ou saída manual. Retorna (movimentação, saldo anterior, saldo atual)."""

    catalogo_service.obter_unidade(db, unidade_id)
    produto = catalogo_service.obter_produto(db, produto_id)

    estoque = estoque_repository.obter(db, unidade_id, produto_id, lock=True)
    if estoque is None:
        raise RecursoNaoEncontradoError(
            "Não há estoque cadastrado para este produto nesta unidade."
        )

    saldo_anterior = estoque.quantidade

    if tipo is TipoMovimentacaoEstoque.ENTRADA:
        estoque.quantidade += quantidade
    elif tipo is TipoMovimentacaoEstoque.SAIDA:
        if quantidade > estoque.disponivel:
            raise EstoqueInsuficienteError(
                f"Saldo disponível insuficiente para {produto.nome} nesta unidade.",
                detalhes=[
                    {
                        "field": "quantidade",
                        "issue": f"Solicitado: {quantidade}, disponível: {estoque.disponivel}",
                    }
                ],
            )
        estoque.quantidade -= quantidade
    else:
        raise EstoqueInsuficienteError("Tipo de movimentação inválido para lançamento manual.")

    movimentacao = MovimentacaoEstoque(
        unidade_id=unidade_id,
        produto_id=produto_id,
        tipo=tipo,
        quantidade=quantidade,
        motivo=motivo,
        usuario_id=usuario.id if usuario else None,
    )
    db.add(movimentacao)

    registrar_auditoria(
        db,
        acao="ESTOQUE_MOVIMENTADO",
        entidade="estoques",
        entidade_id=f"{unidade_id}:{produto_id}",
        usuario_id=usuario.id if usuario else None,
        dados_anteriores={"quantidade": saldo_anterior},
        dados_novos={"quantidade": estoque.quantidade, "tipo": tipo.value, "delta": quantidade},
        request_id=request_id,
    )

    db.commit()
    db.refresh(movimentacao)
    db.refresh(estoque)
    return movimentacao, saldo_anterior, estoque.quantidade
