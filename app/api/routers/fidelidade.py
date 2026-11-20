from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import Paginacao, get_current_user, meta_paginacao, paginacao
from app.api.schemas.base import MetaPaginacao, Pagina
from app.api.schemas.fidelidade import ExtratoItemOut, RegrasFidelidadeOut, SaldoOut
from app.application import fidelidade_service
from app.infrastructure.db.models import Usuario
from app.infrastructure.db.session import get_db

router = APIRouter(prefix="/fidelidade", tags=["Fidelidade"])


@router.get(
    "/saldo",
    response_model=SaldoOut,
    summary="Saldo de pontos do cliente autenticado",
    responses={403: {"description": "Cliente consultando saldo de outro"}, 404: {"description": "Cliente inexistente"}},
)
def consultar_saldo(
    cliente_id: int | None = Query(
        None, alias="clienteId", gt=0, description="Obrigatório para perfis de gestão"
    ),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> SaldoOut:
    return SaldoOut(
        **fidelidade_service.consultar_saldo(db, usuario=usuario, cliente_id=cliente_id)
    )


@router.get(
    "/extrato",
    response_model=Pagina[ExtratoItemOut],
    summary="Histórico de créditos e débitos de pontos",
)
def consultar_extrato(
    pag: Paginacao = Depends(paginacao),
    cliente_id: int | None = Query(None, alias="clienteId", gt=0),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> Pagina[ExtratoItemOut]:
    itens, total = fidelidade_service.extrato(
        db, usuario=usuario, cliente_id=cliente_id, offset=pag.offset, limit=pag.limit
    )
    return Pagina[ExtratoItemOut](
        data=[
            ExtratoItemOut(
                id=item.id,
                tipo=item.tipo,
                pontos=item.pontos,
                descricao=item.descricao,
                pedido_id=item.pedido_id,
                criado_em=item.criado_em,
            )
            for item in itens
        ],
        meta=MetaPaginacao(**meta_paginacao(pag, total)),
    )


@router.get(
    "/regras",
    response_model=RegrasFidelidadeOut,
    summary="Regras vigentes do programa de fidelização",
)
def consultar_regras() -> RegrasFidelidadeOut:
    return RegrasFidelidadeOut(**fidelidade_service.regras())
