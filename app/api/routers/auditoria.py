from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import Paginacao, meta_paginacao, paginacao, require_perfis
from app.api.schemas.auditoria import AuditoriaOut
from app.api.schemas.base import MetaPaginacao, Pagina
from app.application import auditoria as auditoria_service
from app.domain.enums import PerfilUsuario
from app.infrastructure.db.models import Usuario
from app.infrastructure.db.session import get_db

router = APIRouter(prefix="/auditoria", tags=["Auditoria"])

ADMIN = require_perfis(PerfilUsuario.ADMIN)


@router.get(
    "",
    response_model=Pagina[AuditoriaOut],
    summary="Consulta o log append-only de ações sensíveis (somente ADMIN)",
    responses={403: {"description": "Perfil sem permissão"}},
)
def listar_auditoria(
    pag: Paginacao = Depends(paginacao),
    acao: str | None = Query(None, max_length=60, examples=["PEDIDO_CRIADO"]),
    entidade: str | None = Query(None, max_length=60, examples=["pedidos"]),
    entidade_id: str | None = Query(None, alias="entidadeId", max_length=60),
    db: Session = Depends(get_db),
    _: Usuario = Depends(ADMIN),
) -> Pagina[AuditoriaOut]:
    itens, total = auditoria_service.listar(
        db,
        offset=pag.offset,
        limit=pag.limit,
        acao=acao,
        entidade=entidade,
        entidade_id=entidade_id,
    )
    return Pagina[AuditoriaOut](
        data=[
            AuditoriaOut(
                id=item.id,
                usuario_id=item.usuario_id,
                acao=item.acao,
                entidade=item.entidade,
                entidade_id=item.entidade_id,
                dados_novos=item.dados_novos,
                request_id=item.request_id,
                ip=item.ip,
                criado_em=item.criado_em,
            )
            for item in itens
        ],
        meta=MetaPaginacao(**meta_paginacao(pag, total)),
    )
