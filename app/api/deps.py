"""Dependências de autenticação e autorização.

Uso:
    usuario: Usuario = Depends(get_current_user)
    usuario: Usuario = Depends(require_perfis(PerfilUsuario.GERENTE))
"""

from dataclasses import dataclass

from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.domain.enums import PerfilUsuario
from app.domain.exceptions import NaoAutenticadoError, SemPermissaoError, TokenInvalidoError
from app.infrastructure.db.models import Usuario
from app.infrastructure.db.session import get_db
from app.infrastructure.security.tokens import decodificar_access_token

bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="BearerAuth",
    description="Token JWT obtido em POST /auth/login",
)


def get_current_user(
    credenciais: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    if credenciais is None or credenciais.scheme.lower() != "bearer":
        raise NaoAutenticadoError()

    payload = decodificar_access_token(credenciais.credentials)

    try:
        usuario_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise TokenInvalidoError() from exc

    usuario = db.get(Usuario, usuario_id)
    if usuario is None or not usuario.ativo:
        raise TokenInvalidoError("Usuário inexistente ou inativo.")
    return usuario


def require_perfis(*perfis: PerfilUsuario):
    """Fábrica de dependência que restringe o endpoint a certos perfis."""

    permitidos = set(perfis)

    def _verificar(usuario: Usuario = Depends(get_current_user)) -> Usuario:
        if usuario.perfil not in permitidos:
            raise SemPermissaoError(
                f"Acesso restrito aos perfis: {', '.join(p.value for p in perfis)}."
            )
        return usuario

    return _verificar


@dataclass(frozen=True)
class Paginacao:
    page: int
    limit: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit


def paginacao(
    page: int = Query(1, ge=1, description="Página, começando em 1", examples=[1]),
    limit: int = Query(20, ge=1, le=100, description="Itens por página (máx. 100)", examples=[20]),
) -> Paginacao:
    return Paginacao(page=page, limit=limit)


def meta_paginacao(pag: Paginacao, total: int) -> dict:
    total_pages = (total + pag.limit - 1) // pag.limit if total else 0
    return {
        "page": pag.page,
        "limit": pag.limit,
        "total": total,
        "total_pages": total_pages,
    }
