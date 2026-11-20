from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.contexto import request_id
from app.api.deps import Paginacao, get_current_user, meta_paginacao, paginacao
from app.api.schemas.base import MetaPaginacao, Pagina
from app.api.schemas.pedidos import (
    PedidoCreate,
    PedidoItemOut,
    PedidoOut,
    PedidoStatusUpdate,
)
from app.api.schemas.pagamentos import PagamentoOut
from app.api.routers.pagamentos import pagamento_out
from app.application import pagamento_service, pedido_service
from app.domain.enums import CanalPedido, StatusPedido
from app.infrastructure.db.models import Pedido, Usuario
from app.infrastructure.db.session import get_db

router = APIRouter(prefix="/pedidos", tags=["Pedidos"])


def _pedido_out(pedido: Pedido) -> PedidoOut:
    return PedidoOut(
        id=pedido.id,
        cliente_id=pedido.cliente_id,
        unidade_id=pedido.unidade_id,
        canal_pedido=pedido.canal_pedido,
        status=pedido.status,
        forma_pagamento=pedido.forma_pagamento,
        subtotal_itens=pedido.total + pedido.desconto,
        desconto=pedido.desconto,
        pontos_resgatados=pedido.pontos_resgatados,
        total=pedido.total,
        observacao=pedido.observacao,
        criado_em=pedido.criado_em,
        atualizado_em=pedido.atualizado_em,
        itens=[
            PedidoItemOut(
                produto_id=item.produto_id,
                nome=item.produto.nome,
                quantidade=item.quantidade,
                preco_unitario=item.preco_unitario,
                subtotal=item.subtotal,
            )
            for item in pedido.itens
        ],
    )


@router.post(
    "",
    response_model=PedidoOut,
    status_code=status.HTTP_201_CREATED,
    summary="Cria pedido multicanal com reserva de estoque",
    responses={
        404: {"description": "Unidade, produto ou estoque inexistente"},
        409: {"description": "Estoque insuficiente ou produto indisponível"},
        422: {"description": "Payload inválido (ex.: canalPedido ausente)"},
    },
)
def criar_pedido(
    dados: PedidoCreate,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> PedidoOut:
    pedido = pedido_service.criar_pedido(
        db,
        canal_pedido=dados.canal_pedido,
        unidade_id=dados.unidade_id,
        itens=[(item.produto_id, item.quantidade) for item in dados.itens],
        forma_pagamento=dados.forma_pagamento,
        cliente_id=dados.cliente_id,
        observacao=dados.observacao,
        usuario=usuario,
        resgatar_pontos=dados.resgatar_pontos,
        request_id=request_id(request),
    )
    return _pedido_out(pedido)


@router.get(
    "",
    response_model=Pagina[PedidoOut],
    summary="Lista pedidos com filtro por canal e status",
)
def listar_pedidos(
    pag: Paginacao = Depends(paginacao),
    canal_pedido: CanalPedido | None = Query(
        None, alias="canalPedido", description="Filtra pelo canal de origem"
    ),
    status_pedido: StatusPedido | None = Query(None, alias="status"),
    unidade_id: int | None = Query(None, alias="unidadeId", gt=0),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> Pagina[PedidoOut]:
    itens, total = pedido_service.listar_pedidos(
        db,
        usuario=usuario,
        offset=pag.offset,
        limit=pag.limit,
        canal_pedido=canal_pedido,
        status=status_pedido,
        unidade_id=unidade_id,
    )
    return Pagina[PedidoOut](
        data=[_pedido_out(p) for p in itens],
        meta=MetaPaginacao(**meta_paginacao(pag, total)),
    )


@router.get(
    "/{pedido_id}",
    response_model=PedidoOut,
    summary="Consulta um pedido",
    responses={403: {"description": "Cliente tentando acessar pedido de outro"}, 404: {"description": "Pedido inexistente"}},
)
def obter_pedido(
    pedido_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> PedidoOut:
    pedido = pedido_service.obter_pedido(db, pedido_id, usuario=usuario)
    return _pedido_out(pedido)


@router.patch(
    "/{pedido_id}/status",
    response_model=PedidoOut,
    summary="Atualiza o status do pedido respeitando transições e perfis",
    responses={
        403: {"description": "Perfil sem permissão para esta transição"},
        404: {"description": "Pedido inexistente"},
        409: {"description": "Transição de status inválida"},
    },
)
def atualizar_status(
    pedido_id: int,
    dados: PedidoStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> PedidoOut:
    pedido = pedido_service.atualizar_status(
        db,
        pedido_id,
        novo_status=dados.status,
        usuario=usuario,
        observacao=dados.observacao,
        request_id=request_id(request),
    )
    return _pedido_out(pedido)


@router.get(
    "/{pedido_id}/pagamentos",
    response_model=list[PagamentoOut],
    summary="Lista as tentativas de pagamento de um pedido",
    responses={403: {"description": "Pedido de outro cliente"}, 404: {"description": "Pedido inexistente"}},
)
def listar_pagamentos(
    pedido_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> list[PagamentoOut]:
    pagamentos = pagamento_service.listar_por_pedido(db, pedido_id, usuario=usuario)
    return [pagamento_out(db, p) for p in pagamentos]
