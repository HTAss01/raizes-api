"""Consultas do programa de fidelização.

O resgate é aplicado na criação do pedido (campo `resgatarPontos`), o que
evita crédito órfão: o débito nasce amarrado a um pedido concreto.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.enums import PerfilUsuario, TipoTransacaoPontos
from app.domain.exceptions import RecursoNaoEncontradoError, RegraNegocioError, SemPermissaoError
from app.domain.rules.fidelidade import PONTOS_POR_RESGATE, PONTOS_POR_REAL, VALOR_DO_RESGATE
from app.infrastructure.db.models import PontoTransacao, Usuario


def resolver_cliente(cliente_id: int | None, usuario: Usuario) -> int:
    """Cliente só consulta o próprio saldo; staff precisa informar clienteId."""

    if usuario.perfil is PerfilUsuario.CLIENTE:
        if cliente_id is not None and cliente_id != usuario.id:
            raise SemPermissaoError("Você só pode consultar o seu próprio saldo de pontos.")
        return usuario.id

    if cliente_id is None:
        raise RegraNegocioError(
            "Informe o clienteId para consultar a fidelidade.",
            detalhes=[{"field": "clienteId", "issue": "Obrigatório para perfis de gestão"}],
        )
    return cliente_id


def saldo_pontos(db: Session, cliente_id: int) -> int:
    def _soma(tipo: TipoTransacaoPontos) -> int:
        valor = db.scalar(
            select(func.coalesce(func.sum(PontoTransacao.pontos), 0)).where(
                PontoTransacao.cliente_id == cliente_id,
                PontoTransacao.tipo == tipo,
            )
        )
        return int(valor or 0)

    return _soma(TipoTransacaoPontos.CREDITO) - _soma(TipoTransacaoPontos.DEBITO)


def consultar_saldo(db: Session, *, usuario: Usuario, cliente_id: int | None = None) -> dict:
    alvo = resolver_cliente(cliente_id, usuario)
    if db.get(Usuario, alvo) is None:
        raise RecursoNaoEncontradoError("Cliente não encontrado.")

    saldo = saldo_pontos(db, alvo)
    resgates = saldo // PONTOS_POR_RESGATE
    return {
        "cliente_id": alvo,
        "saldo_pontos": saldo,
        "valor_disponivel": float(VALOR_DO_RESGATE * resgates),
        "resgates_disponiveis": resgates,
        "pontos_para_proximo_resgate": 0 if resgates else PONTOS_POR_RESGATE - saldo,
    }


def extrato(
    db: Session,
    *,
    usuario: Usuario,
    cliente_id: int | None = None,
    offset: int,
    limit: int,
) -> tuple[list[PontoTransacao], int]:
    alvo = resolver_cliente(cliente_id, usuario)
    stmt = select(PontoTransacao).where(PontoTransacao.cliente_id == alvo)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    itens = list(
        db.scalars(
            stmt.order_by(PontoTransacao.criado_em.desc(), PontoTransacao.id.desc())
            .offset(offset)
            .limit(limit)
        )
    )
    return itens, total


def regras() -> dict:
    return {
        "pontos_por_real": float(PONTOS_POR_REAL),
        "pontos_por_resgate": PONTOS_POR_RESGATE,
        "valor_do_resgate": float(VALOR_DO_RESGATE),
        "consentimento_obrigatorio": True,
    }
