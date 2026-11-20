from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.api.contexto import ip_origem, request_id
from app.api.deps import Paginacao, get_current_user, meta_paginacao, paginacao, require_perfis
from app.api.schemas.base import MetaPaginacao, Pagina
from app.api.schemas.usuarios import (
    ExportacaoDadosOut,
    PedidoResumoOut,
    PontoResumoOut,
    UsuarioCreate,
    UsuarioListaOut,
    UsuarioOut,
    UsuarioUpdateMe,
)
from app.application import usuario_service
from app.domain.enums import PerfilUsuario
from app.infrastructure.db.models import Usuario
from app.infrastructure.db.session import get_db

router = APIRouter(prefix="/usuarios", tags=["Usuários"])

GESTAO = require_perfis(PerfilUsuario.ADMIN, PerfilUsuario.GERENTE)


@router.post(
    "",
    response_model=UsuarioOut,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra um cliente (autocadastro público)",
    responses={409: {"description": "E-mail já cadastrado"}},
)
def cadastrar(
    dados: UsuarioCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> UsuarioOut:
    usuario = usuario_service.cadastrar(
        db,
        nome=dados.nome,
        email=dados.email,
        senha=dados.senha,
        telefone=dados.telefone,
        consentimento_lgpd=dados.consentimento_lgpd,
        request_id=request_id(request),
        ip=ip_origem(request),
    )
    return UsuarioOut.model_validate(usuario)


@router.get(
    "/me",
    response_model=UsuarioOut,
    summary="Dados do próprio titular (acesso auditado)",
)
def meus_dados(
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> UsuarioOut:
    usuario = usuario_service.dados_do_titular(
        db, usuario, request_id=request_id(request), ip=ip_origem(request)
    )
    return UsuarioOut.model_validate(usuario)


@router.patch(
    "/me",
    response_model=UsuarioOut,
    summary="Atualiza nome ou telefone do próprio titular",
)
def atualizar_meus_dados(
    dados: UsuarioUpdateMe,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> UsuarioOut:
    alteracoes = dados.model_dump(exclude_unset=True, exclude_none=True)
    usuario = usuario_service.atualizar_titular(
        db, usuario, alteracoes=alteracoes, request_id=request_id(request)
    )
    return UsuarioOut.model_validate(usuario)


@router.get(
    "",
    response_model=Pagina[UsuarioListaOut],
    summary="Lista usuários da rede (gestão)",
    responses={403: {"description": "Perfil sem permissão"}},
)
def listar_usuarios(
    pag: Paginacao = Depends(paginacao),
    perfil: PerfilUsuario | None = Query(None, description="Filtra por perfil"),
    ativo: bool | None = Query(None),
    db: Session = Depends(get_db),
    _: Usuario = Depends(GESTAO),
) -> Pagina[UsuarioListaOut]:
    itens, total = usuario_service.listar(
        db, offset=pag.offset, limit=pag.limit, perfil=perfil, ativo=ativo
    )
    return Pagina[UsuarioListaOut](
        data=[UsuarioListaOut.model_validate(u) for u in itens],
        meta=MetaPaginacao(**meta_paginacao(pag, total)),
    )


@router.get(
    "/me/dados",
    response_model=ExportacaoDadosOut,
    summary="Portabilidade: exporta todos os dados pessoais do titular",
)
def exportar_meus_dados(
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> ExportacaoDadosOut:
    dados = usuario_service.exportar_dados(
        db, usuario, request_id=request_id(request), ip=ip_origem(request)
    )
    return ExportacaoDadosOut(
        gerado_em=dados["gerado_em"],
        usuario=UsuarioOut.model_validate(dados["usuario"]),
        pedidos=[
            PedidoResumoOut(
                id=pedido.id,
                canal_pedido=pedido.canal_pedido,
                status=pedido.status,
                total=pedido.total,
                criado_em=pedido.criado_em,
            )
            for pedido in dados["pedidos"]
        ],
        pontos=[
            PontoResumoOut(
                id=ponto.id,
                tipo=ponto.tipo,
                pontos=ponto.pontos,
                descricao=ponto.descricao,
                criado_em=ponto.criado_em,
            )
            for ponto in dados["pontos"]
        ],
    )


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Elimina a conta com anonimização dos dados pessoais (LGPD)",
)
def eliminar_minha_conta(
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
) -> Response:
    usuario_service.anonimizar(
        db, usuario, request_id=request_id(request), ip=ip_origem(request)
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
