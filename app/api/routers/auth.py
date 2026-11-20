from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.schemas.auth import LoginRequest, RefreshRequest, TokenResponse, UsuarioResumo
from app.application import auth_service
from app.infrastructure.db.models import Usuario
from app.infrastructure.db.session import get_db

router = APIRouter(prefix="/auth", tags=["Autenticação"])


def _contexto(request: Request) -> tuple[str | None, str | None]:
    request_id = getattr(request.state, "request_id", None)
    ip = request.client.host if request.client else None
    return request_id, ip


def _token_response(usuario: Usuario, tokens: auth_service.TokensEmitidos) -> TokenResponse:
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
        user=UsuarioResumo.model_validate(usuario),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Autentica o usuário e devolve os tokens",
    responses={401: {"description": "Credenciais inválidas"}},
)
def login(dados: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    request_id, ip = _contexto(request)
    usuario = auth_service.autenticar(
        db, email=dados.email, senha=dados.senha, request_id=request_id, ip=ip
    )
    tokens = auth_service.abrir_sessao(db, usuario)
    return _token_response(usuario, tokens)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Troca um refresh token válido por um novo par de tokens",
    responses={401: {"description": "Refresh token inválido, expirado ou revogado"}},
)
def refresh(dados: RefreshRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    request_id, _ = _contexto(request)
    usuario, tokens = auth_service.renovar_sessao(
        db, dados.refresh_token, request_id=request_id
    )
    return _token_response(usuario, tokens)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoga o refresh token (idempotente)",
)
def logout(dados: RefreshRequest, request: Request, db: Session = Depends(get_db)) -> Response:
    request_id, _ = _contexto(request)
    auth_service.revogar_sessao(db, dados.refresh_token, request_id=request_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/me",
    response_model=UsuarioResumo,
    summary="Retorna o usuário autenticado",
    responses={401: {"description": "Token ausente, inválido ou expirado"}},
)
def me(usuario: Usuario = Depends(get_current_user)) -> Usuario:
    return usuario
