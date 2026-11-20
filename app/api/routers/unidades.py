from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.contexto import ip_origem, request_id
from app.api.deps import Paginacao, get_current_user, meta_paginacao, paginacao, require_perfis
from app.api.schemas.base import MetaPaginacao, Pagina
from app.api.schemas.catalogo import (
    CardapioItemOut,
    CardapioItemUpdate,
    UnidadeCreate,
    UnidadeOut,
)
from app.api.schemas.estoque import EstoqueOut, MovimentacaoCreate, MovimentacaoOut
from app.application import catalogo_service, estoque_service
from app.domain.enums import PerfilUsuario
from app.infrastructure.db.models import Usuario
from app.infrastructure.db.session import get_db

router = APIRouter(prefix="/unidades", tags=["Unidades"])

OPERACAO = require_perfis(
    PerfilUsuario.ADMIN,
    PerfilUsuario.GERENTE,
    PerfilUsuario.ATENDENTE,
    PerfilUsuario.COZINHA,
)
GESTAO = require_perfis(PerfilUsuario.ADMIN, PerfilUsuario.GERENTE)


@router.get("", response_model=Pagina[UnidadeOut], summary="Lista as unidades da rede")
def listar_unidades(
    pag: Paginacao = Depends(paginacao),
    somente_ativas: bool = Query(True, alias="somenteAtivas", description="Oculta unidades desativadas"),
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
) -> Pagina[UnidadeOut]:
    itens, total = catalogo_service.listar_unidades(
        db, offset=pag.offset, limit=pag.limit, apenas_ativas=somente_ativas
    )
    return Pagina[UnidadeOut](
        data=[UnidadeOut.model_validate(u) for u in itens],
        meta=MetaPaginacao(**meta_paginacao(pag, total)),
    )


@router.get("/{unidade_id}", response_model=UnidadeOut, summary="Consulta uma unidade")
def obter_unidade(
    unidade_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
) -> UnidadeOut:
    return UnidadeOut.model_validate(catalogo_service.obter_unidade(db, unidade_id))


@router.post(
    "",
    response_model=UnidadeOut,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra uma nova unidade",
    responses={403: {"description": "Perfil sem permissão"}},
)
def criar_unidade(
    dados: UnidadeCreate,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(GESTAO),
) -> UnidadeOut:
    unidade = catalogo_service.criar_unidade(
        db,
        dados.model_dump(),
        usuario_id=usuario.id,
        request_id=request_id(request),
    )
    return UnidadeOut.model_validate(unidade)


@router.get(
    "/{unidade_id}/cardapio",
    response_model=Pagina[CardapioItemOut],
    summary="Cardápio da unidade, com preço, disponibilidade e saldo",
)
def listar_cardapio(
    unidade_id: int,
    pag: Paginacao = Depends(paginacao),
    categoria: str | None = Query(None, max_length=60, examples=["SALGADOS"]),
    apenas_disponiveis: bool = Query(False, alias="apenasDisponiveis"),
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
) -> Pagina[CardapioItemOut]:
    itens, total = catalogo_service.listar_cardapio(
        db,
        unidade_id,
        categoria=categoria,
        apenas_disponiveis=apenas_disponiveis,
        offset=pag.offset,
        limit=pag.limit,
    )
    return Pagina[CardapioItemOut](
        data=[CardapioItemOut(**item) for item in itens],
        meta=MetaPaginacao(**meta_paginacao(pag, total)),
    )


@router.put(
    "/{unidade_id}/cardapio/{produto_id}",
    response_model=CardapioItemOut,
    summary="Ajusta preço e disponibilidade de um item no cardápio da unidade",
    responses={403: {"description": "Perfil sem permissão"}, 404: {"description": "Unidade ou produto inexistente"}},
)
def atualizar_item_cardapio(
    unidade_id: int,
    produto_id: int,
    dados: CardapioItemUpdate,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(GESTAO),
) -> CardapioItemOut:
    catalogo_service.definir_item_cardapio(
        db,
        unidade_id,
        produto_id,
        preco=dados.preco,
        disponivel=dados.disponivel,
        usuario_id=usuario.id,
        request_id=request_id(request),
    )
    itens, _ = catalogo_service.listar_cardapio(db, unidade_id)
    item = next(i for i in itens if i["produto_id"] == produto_id)
    return CardapioItemOut(**item)


@router.get(
    "/{unidade_id}/estoque",
    response_model=Pagina[EstoqueOut],
    summary="Saldo de estoque por produto da unidade",
    responses={403: {"description": "Cliente não acessa estoque bruto"}},
)
def listar_estoque(
    unidade_id: int,
    pag: Paginacao = Depends(paginacao),
    db: Session = Depends(get_db),
    _: Usuario = Depends(OPERACAO),
) -> Pagina[EstoqueOut]:
    itens, total = estoque_service.listar_estoque(
        db, unidade_id, offset=pag.offset, limit=pag.limit
    )
    return Pagina[EstoqueOut](
        data=[EstoqueOut(**item) for item in itens],
        meta=MetaPaginacao(**meta_paginacao(pag, total)),
    )


@router.post(
    "/{unidade_id}/estoque/movimentacoes",
    response_model=MovimentacaoOut,
    status_code=status.HTTP_201_CREATED,
    summary="Registra entrada ou saída manual de estoque",
    responses={
        403: {"description": "Perfil sem permissão"},
        404: {"description": "Unidade, produto ou estoque inexistente"},
        409: {"description": "Saldo insuficiente para a saída"},
    },
)
def movimentar_estoque(
    unidade_id: int,
    dados: MovimentacaoCreate,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(GESTAO),
) -> MovimentacaoOut:
    movimentacao, saldo_anterior, saldo_atual = estoque_service.movimentar(
        db,
        unidade_id=unidade_id,
        produto_id=dados.produto_id,
        tipo=dados.tipo,
        quantidade=dados.quantidade,
        motivo=dados.motivo,
        usuario=usuario,
        request_id=request_id(request),
    )
    return MovimentacaoOut(
        id=movimentacao.id,
        produto_id=movimentacao.produto_id,
        tipo=movimentacao.tipo,
        quantidade=movimentacao.quantidade,
        motivo=movimentacao.motivo,
        quantidade_apos=saldo_atual,
        saldo_anterior=saldo_anterior,
        criado_em=movimentacao.criado_em,
    )
