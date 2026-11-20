from fastapi import APIRouter, Depends, Header, Request, Response, status
from sqlalchemy.orm import Session

from app.api.contexto import request_id
from app.api.deps import get_current_user
from app.api.schemas.pagamentos import PagamentoCreate, PagamentoOut
from app.application import pagamento_service
from app.infrastructure.db.models import Pagamento, Usuario
from app.infrastructure.db.session import get_db

router = APIRouter(prefix="/pagamentos", tags=["Pagamentos"])


def pagamento_out(db: Session, pagamento: Pagamento) -> PagamentoOut:
    return PagamentoOut(
        id=pagamento.id,
        pedido_id=pagamento.pedido_id,
        pedido_status=pagamento_service.status_do_pedido(db, pagamento),
        status=pagamento.status,
        valor=pagamento.valor,
        forma_pagamento=pagamento.forma_pagamento,
        idempotency_key=pagamento.idempotency_key,
        transacao_externa_id=pagamento.transacao_externa_id,
        motivo_recusa=pagamento.motivo_recusa,
        payload_resposta=pagamento.payload_resposta,
        criado_em=pagamento.criado_em,
        processado_em=pagamento.processado_em,
    )


@router.post(
    "",
    response_model=PagamentoOut,
    status_code=status.HTTP_201_CREATED,
    summary="Solicita pagamento ao gateway mock (idempotente)",
    responses={
        200: {"description": "Replay idempotente: devolve o pagamento já registrado"},
        403: {"description": "Pedido de outro cliente"},
        404: {"description": "Pedido inexistente"},
        409: {"description": "Pedido já processado ou chave reutilizada"},
        422: {"description": "Idempotency-Key ausente ou payload inválido"},
    },
)
def processar_pagamento(
    dados: PagamentoCreate,
    request: Request,
    response: Response,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=120),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> PagamentoOut:
    pagamento, criado_agora = pagamento_service.processar(
        db,
        pedido_id=dados.pedido_id,
        idempotency_key=idempotency_key,
        simular_resultado=dados.simular_resultado,
        motivo_recusa=dados.motivo_recusa,
        usuario=usuario,
        request_id=request_id(request),
    )
    if not criado_agora:
        response.status_code = status.HTTP_200_OK
    return pagamento_out(db, pagamento)


@router.get(
    "/{pagamento_id}",
    response_model=PagamentoOut,
    summary="Consulta um pagamento",
    responses={403: {"description": "Pagamento de outro cliente"}, 404: {"description": "Pagamento inexistente"}},
)
def obter_pagamento(
    pagamento_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> PagamentoOut:
    pagamento = pagamento_service.obter(db, pagamento_id, usuario=usuario)
    return pagamento_out(db, pagamento)
