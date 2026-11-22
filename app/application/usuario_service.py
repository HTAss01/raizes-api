"""Casos de uso de usuários (cadastro, dados do titular, gestão e LGPD)."""

import secrets

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.application.auditoria import mascarar_email, registrar_auditoria
from app.domain.enums import PerfilUsuario
from app.domain.exceptions import EmailJaCadastradoError, RecursoNaoEncontradoError
from app.infrastructure.db.models import Pedido, PontoTransacao, Usuario
from app.infrastructure.security.password import hash_senha
from app.infrastructure.security.tokens import agora


def _por_email(db: Session, email: str) -> Usuario | None:
    return db.scalar(select(Usuario).where(Usuario.email == email.strip().lower()))


def cadastrar(
    db: Session,
    *,
    nome: str,
    email: str,
    senha: str,
    telefone: str | None,
    consentimento_lgpd: bool,
    perfil: PerfilUsuario,
    request_id: str | None = None,
    ip: str | None = None,
) -> Usuario:
    """Cadastro de usuário executado por um ADMIN, com perfil explícito."""

    email_normalizado = email.strip().lower()
    if _por_email(db, email_normalizado) is not None:
        raise EmailJaCadastradoError()

    usuario = Usuario(
        nome=nome,
        email=email_normalizado,
        senha_hash=hash_senha(senha),
        telefone=telefone,
        perfil=perfil,
        ativo=True,
        consentimento_lgpd=consentimento_lgpd,
        consentimento_em=agora() if consentimento_lgpd else None,
    )
    db.add(usuario)
    db.flush()

    registrar_auditoria(
        db,
        acao="USUARIO_CADASTRADO",
        entidade="usuarios",
        entidade_id=usuario.id,
        usuario_id=usuario.id,
        dados_novos={
            "perfil": usuario.perfil.value,
            "consentimentoLgpd": consentimento_lgpd,
            "finalidade": "execução do contrato e programa de fidelização",
        },
        request_id=request_id,
        ip=ip,
    )
    db.commit()
    db.refresh(usuario)
    return usuario


def dados_do_titular(
    db: Session, usuario: Usuario, *, request_id: str | None = None, ip: str | None = None
) -> Usuario:
    """Acesso a dados pessoais é ação auditável (LGPD)."""

    registrar_auditoria(
        db,
        acao="LEITURA_DADOS_PESSOAIS",
        entidade="usuarios",
        entidade_id=usuario.id,
        usuario_id=usuario.id,
        request_id=request_id,
        ip=ip,
    )
    db.commit()
    return usuario


def atualizar_titular(
    db: Session,
    usuario: Usuario,
    *,
    alteracoes: dict,
    request_id: str | None = None,
) -> Usuario:
    if not alteracoes:
        return usuario

    anteriores = {campo: getattr(usuario, campo) for campo in alteracoes}
    for campo, valor in alteracoes.items():
        setattr(usuario, campo, valor)

    registrar_auditoria(
        db,
        acao="USUARIO_ATUALIZADO",
        entidade="usuarios",
        entidade_id=usuario.id,
        usuario_id=usuario.id,
        dados_anteriores=anteriores,
        dados_novos=alteracoes,
        request_id=request_id,
    )
    db.commit()
    db.refresh(usuario)
    return usuario


def listar(
    db: Session,
    *,
    offset: int,
    limit: int,
    perfil: PerfilUsuario | None = None,
    ativo: bool | None = None,
) -> tuple[list[Usuario], int]:
    stmt = select(Usuario)
    if perfil is not None:
        stmt = stmt.where(Usuario.perfil == perfil)
    if ativo is not None:
        stmt = stmt.where(Usuario.ativo.is_(ativo))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    itens = list(db.scalars(stmt.order_by(Usuario.nome).offset(offset).limit(limit)))
    return itens, total


def obter(db: Session, usuario_id: int) -> Usuario:
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise RecursoNaoEncontradoError("Usuário não encontrado.")
    return usuario


def exportar_dados(
    db: Session, usuario: Usuario, *, request_id: str | None = None, ip: str | None = None
) -> dict:
    """Portabilidade (LGPD art. 18, V): devolve tudo que a API guarda do titular."""

    pedidos = list(
        db.scalars(
            select(Pedido).where(Pedido.cliente_id == usuario.id).order_by(Pedido.id)
        )
    )
    pontos = list(
        db.scalars(
            select(PontoTransacao)
            .where(PontoTransacao.cliente_id == usuario.id)
            .order_by(PontoTransacao.id)
        )
    )

    registrar_auditoria(
        db,
        acao="EXPORTACAO_DADOS_PESSOAIS",
        entidade="usuarios",
        entidade_id=usuario.id,
        usuario_id=usuario.id,
        dados_novos={"pedidos": len(pedidos), "transacoesPontos": len(pontos)},
        request_id=request_id,
        ip=ip,
    )
    db.commit()

    return {
        "gerado_em": agora(),
        "usuario": usuario,
        "pedidos": pedidos,
        "pontos": pontos,
    }


def anonimizar(
    db: Session, usuario: Usuario, *, request_id: str | None = None, ip: str | None = None
) -> None:
    """Eliminação com anonimização (LGPD art. 18, VI).

    Os registros de pedido permanecem (obrigação fiscal/contábil), mas deixam de
    apontar para dados pessoais: nome genérico, e-mail sintético, contato limpo,
    senha aleatória descartada, tokens revogados e conta inativa.
    """

    email_original = usuario.email

    usuario.nome = "Titular anonimizado"
    usuario.email = f"anonimizado+{usuario.id}@removido.invalid"
    usuario.telefone = None
    usuario.senha_hash = hash_senha(secrets.token_urlsafe(32))
    usuario.ativo = False
    usuario.consentimento_lgpd = False
    usuario.consentimento_em = None

    for token in usuario.refresh_tokens:
        token.revogado = True

    registrar_auditoria(
        db,
        acao="LGPD_ANONIMIZACAO",
        entidade="usuarios",
        entidade_id=usuario.id,
        usuario_id=usuario.id,
        dados_anteriores={"email": mascarar_email(email_original)},
        dados_novos={
            "email": "removido",
            "pedidosPreservados": True,
            "motivo": "exercício do direito de eliminação",
        },
        request_id=request_id,
        ip=ip,
    )
    db.commit()

