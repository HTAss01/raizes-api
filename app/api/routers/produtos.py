from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.api.contexto import request_id
from app.api.deps import Paginacao, get_current_user, meta_paginacao, paginacao, require_perfis
from app.api.schemas.base import MetaPaginacao, Pagina
from app.api.schemas.catalogo import ProdutoCreate, ProdutoOut, ProdutoUpdate
from app.application import catalogo_service
from app.domain.enums import PerfilUsuario
from app.infrastructure.db.models import Usuario
from app.infrastructure.db.session import get_db

router = APIRouter(prefix="/produtos", tags=["Produtos"])

GESTAO = require_perfis(PerfilUsuario.ADMIN, PerfilUsuario.GERENTE)


@router.get("", response_model=Pagina[ProdutoOut], summary="Lista produtos com filtros")
def listar_produtos(
    pag: Paginacao = Depends(paginacao),
    categoria: str | None = Query(None, max_length=60, examples=["BEBIDAS"]),
    ativo: bool | None = Query(None, description="Filtra por produtos ativos/inativos"),
    busca: str | None = Query(None, alias="q", max_length=60, description="Busca por nome"),
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
) -> Pagina[ProdutoOut]:
    itens, total = catalogo_service.listar_produtos(
        db, offset=pag.offset, limit=pag.limit, categoria=categoria, ativo=ativo, busca=busca
    )
    return Pagina[ProdutoOut](
        data=[ProdutoOut.model_validate(p) for p in itens],
        meta=MetaPaginacao(**meta_paginacao(pag, total)),
    )


@router.get("/{produto_id}", response_model=ProdutoOut, summary="Consulta um produto")
def obter_produto(
    produto_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
) -> ProdutoOut:
    return ProdutoOut.model_validate(catalogo_service.obter_produto(db, produto_id))


@router.post(
    "",
    response_model=ProdutoOut,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra produto e já o habilita nas unidades ativas",
    responses={403: {"description": "Perfil sem permissão"}},
)
def criar_produto(
    dados: ProdutoCreate,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(GESTAO),
) -> ProdutoOut:
    produto = catalogo_service.criar_produto(
        db, dados.model_dump(), usuario_id=usuario.id, request_id=request_id(request)
    )
    return ProdutoOut.model_validate(produto)


@router.patch(
    "/{produto_id}",
    response_model=ProdutoOut,
    summary="Atualiza parcialmente um produto",
    responses={403: {"description": "Perfil sem permissão"}, 404: {"description": "Produto inexistente"}},
)
def atualizar_produto(
    produto_id: int,
    dados: ProdutoUpdate,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(GESTAO),
) -> ProdutoOut:
    alteracoes = dados.model_dump(exclude_unset=True, exclude_none=True)
    produto = catalogo_service.atualizar_produto(
        db,
        produto_id,
        alteracoes,
        usuario_id=usuario.id,
        request_id=request_id(request),
    )
    return ProdutoOut.model_validate(produto)


@router.delete(
    "/{produto_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Desativa um produto (exclusão lógica)",
    responses={403: {"description": "Perfil sem permissão"}, 404: {"description": "Produto inexistente"}},
)
def desativar_produto(
    produto_id: int,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(GESTAO),
) -> Response:
    catalogo_service.desativar_produto(
        db, produto_id, usuario_id=usuario.id, request_id=request_id(request)
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
