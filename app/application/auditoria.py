"""Registro de auditoria de ações sensíveis (LGPD e rastreabilidade).

O log é append-only: nunca é atualizado nem apagado pela aplicação.
"""

from sqlalchemy.orm import Session

from app.infrastructure.db.models import LogAuditoria


def mascarar_email(email: str) -> str:
    """Minimização de dados: não grava o e-mail completo em log de falha."""

    if "@" not in email:
        return "***"
    local, dominio = email.split("@", 1)
    visivel = local[:2]
    return f"{visivel}***@{dominio}"


def registrar_auditoria(
    db: Session,
    *,
    acao: str,
    entidade: str,
    entidade_id: str | int | None = None,
    usuario_id: int | None = None,
    dados_anteriores: dict | None = None,
    dados_novos: dict | None = None,
    request_id: str | None = None,
    ip: str | None = None,
) -> LogAuditoria:
    log = LogAuditoria(
        acao=acao,
        entidade=entidade,
        entidade_id=str(entidade_id) if entidade_id is not None else None,
        usuario_id=usuario_id,
        dados_anteriores=dados_anteriores,
        dados_novos=dados_novos,
        request_id=request_id,
        ip=ip,
    )
    db.add(log)
    return log
