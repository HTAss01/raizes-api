"""Casos de uso de autenticação.

Orquestra repositório, hash de senha, emissão de tokens e auditoria.
Nenhuma regra de HTTP aqui: erros são exceções de domínio.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.auditoria import mascarar_email, registrar_auditoria
from app.domain.exceptions import (
    CredenciaisInvalidasError,
    SemPermissaoError,
    TokenExpiradoError,
    TokenInvalidoError,
)
from app.infrastructure.db.models import RefreshToken, Usuario
from app.infrastructure.security.password import verificar_senha
from app.infrastructure.security.tokens import (
    agora,
    como_utc,
    criar_access_token,
    expiracao_refresh,
    gerar_refresh_token,
    hash_token,
)


@dataclass(frozen=True)
class TokensEmitidos:
    access_token: str
    refresh_token: str
    expires_in: int


def _emitir(db: Session, usuario: Usuario) -> TokensEmitidos:
    access_token, expires_in = criar_access_token(
        usuario_id=usuario.id, perfil=usuario.perfil.value
    )
    refresh_token, refresh_hash = gerar_refresh_token()
    db.add(
        RefreshToken(
            usuario_id=usuario.id,
            token_hash=refresh_hash,
            expira_em=expiracao_refresh(),
            revogado=False,
        )
    )
    return TokensEmitidos(
        access_token=access_token, refresh_token=refresh_token, expires_in=expires_in
    )


def autenticar(
    db: Session,
    *,
    email: str,
    senha: str,
    request_id: str | None = None,
    ip: str | None = None,
) -> Usuario:
    email_normalizado = email.strip().lower()
    usuario = db.scalar(select(Usuario).where(Usuario.email == email_normalizado))

    if usuario is None or not verificar_senha(senha, usuario.senha_hash):
        registrar_auditoria(
            db,
            acao="LOGIN_FALHA",
            entidade="usuarios",
            dados_novos={"email": mascarar_email(email_normalizado)},
            request_id=request_id,
            ip=ip,
        )
        db.commit()
        raise CredenciaisInvalidasError()

    if not usuario.ativo:
        registrar_auditoria(
            db,
            acao="LOGIN_BLOQUEADO",
            entidade="usuarios",
            entidade_id=usuario.id,
            usuario_id=usuario.id,
            request_id=request_id,
            ip=ip,
        )
        db.commit()
        raise SemPermissaoError("Usuário inativo. Procure o administrador da rede.")

    registrar_auditoria(
        db,
        acao="LOGIN_SUCESSO",
        entidade="usuarios",
        entidade_id=usuario.id,
        usuario_id=usuario.id,
        request_id=request_id,
        ip=ip,
    )
    return usuario


def abrir_sessao(db: Session, usuario: Usuario) -> TokensEmitidos:
    tokens = _emitir(db, usuario)
    db.commit()
    return tokens


def renovar_sessao(db: Session, refresh_token: str, request_id: str | None = None) -> tuple[Usuario, TokensEmitidos]:
    registro = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token))
    )

    if registro is None or registro.revogado:
        raise TokenInvalidoError()

    if como_utc(registro.expira_em) <= agora():
        raise TokenExpiradoError()

    usuario = db.get(Usuario, registro.usuario_id)
    if usuario is None or not usuario.ativo:
        raise TokenInvalidoError()

    # Rotação: o refresh usado é revogado e um novo par é emitido.
    registro.revogado = True
    tokens = _emitir(db, usuario)
    registrar_auditoria(
        db,
        acao="TOKEN_RENOVADO",
        entidade="usuarios",
        entidade_id=usuario.id,
        usuario_id=usuario.id,
        request_id=request_id,
    )
    db.commit()
    return usuario, tokens


def revogar_sessao(db: Session, refresh_token: str, request_id: str | None = None) -> None:
    registro = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token))
    )
    if registro is None or registro.revogado:
        return
    registro.revogado = True
    registrar_auditoria(
        db,
        acao="LOGOUT",
        entidade="usuarios",
        entidade_id=registro.usuario_id,
        usuario_id=registro.usuario_id,
        request_id=request_id,
    )
    db.commit()
