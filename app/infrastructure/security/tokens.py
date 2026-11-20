"""Emissão e validação de tokens JWT.

Access token: JWT assinado (HS256) com perfil embutido, para que a
autorização não dependa de uma consulta extra em cada request.
Refresh token: string aleatória persistida apenas como hash SHA-256, com
rotação a cada uso.
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings
from app.domain.exceptions import TokenExpiradoError, TokenInvalidoError


def agora() -> datetime:
    return datetime.now(timezone.utc)


def como_utc(valor: datetime) -> datetime:
    """SQLite devolve datetime sem tzinfo; normaliza antes de comparar."""

    if valor.tzinfo is None:
        return valor.replace(tzinfo=timezone.utc)
    return valor


def criar_access_token(*, usuario_id: int, perfil: str) -> tuple[str, int]:
    expires_in = settings.access_token_expire_minutes * 60
    emitido_em = agora()
    payload = {
        "sub": str(usuario_id),
        "perfil": perfil,
        "tipo": "access",
        "iat": emitido_em,
        "exp": emitido_em + timedelta(seconds=expires_in),
        "jti": uuid.uuid4().hex,
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    return token, expires_in


def decodificar_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiradoError() from exc
    except jwt.PyJWTError as exc:
        raise TokenInvalidoError() from exc

    if payload.get("tipo") != "access" or not payload.get("sub"):
        raise TokenInvalidoError()
    return payload


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def gerar_refresh_token() -> tuple[str, str]:
    """Retorna (token em claro, hash) - apenas o hash vai para o banco."""

    token = secrets.token_urlsafe(48)
    return token, hash_token(token)


def expiracao_refresh() -> datetime:
    return agora() + timedelta(days=settings.refresh_token_expire_days)
