"""Serviço de pagamento simulado (mock).

Garantias do fluxo:
- `Idempotency-Key` obrigatória: repetir a mesma chave devolve o pagamento
  já registrado, sem nova baixa de estoque nem novo crédito de pontos;
- o valor cobrado é sempre o total do pedido (nunca vem do cliente);
- aprovação converte a reserva em baixa e leva o pedido a PAGO;
- recusa libera a reserva e encerra o pedido como CANCELADO;
- pontos são creditados apenas com consentimento LGPD, uma vez por pedido.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.auditoria import registrar_auditoria
from app.config import settings
from app.domain.enums import (
    PerfilUsuario,
    StatusPagamento,
    StatusPedido,
    TipoMovimentacaoEstoque,
    TipoTransacaoPontos,
)
from app.domain.exceptions import (
    ConflitoError,
    PedidoJaProcessadoError,
    RecursoNaoEncontradoError,
    SemPermissaoError,
)
from app.domain.rules.fidelidade import calcular_pontos
from app.domain.rules.status_pedido import validar_transicao
from app.infrastructure.db.models import (
    MovimentacaoEstoque,
    Pagamento,
    Pedido,
    PedidoStatusHistorico,
    PontoTransacao,
    Usuario,
)
from app.infrastructure.db.repositories import estoque_repository, pedido_repository
from app.infrastructure.security.tokens import agora


def _deve_aprovar(simular_resultado: str | None) -> bool:
    if simular_resultado is not None:
        return simular_resultado == "APROVADO"
    return settings.mock_payment_approval_rate >= 100 or (
        uuid.uuid4().int % 100 < settings.mock_payment_approval_rate
    )


def _validar_acesso(pedido: Pedido, usuario: Usuario) -> None:
    if usuario.perfil is PerfilUsuario.CLIENTE and pedido.cliente_id != usuario.id:
        raise SemPermissaoError("Você só pode pagar os seus próprios pedidos.")


def _baixar_reservas(db: Session, pedido: Pedido, usuario: Usuario) -> None:
    for item in pedido.itens:
        estoque = estoque_repository.obter(db, pedido.unidade_id, item.produto_id, lock=True)
        if estoque is None:
            raise RecursoNaoEncontradoError(
                f"Estoque do produto {item.produto_id} não encontrado nesta unidade."
            )
        estoque_repository.baixar(estoque, item.quantidade)
        db.add(
            MovimentacaoEstoque(
                unidade_id=pedido.unidade_id,
                produto_id=item.produto_id,
                tipo=TipoMovimentacaoEstoque.BAIXA,
                quantidade=item.quantidade,
                motivo=f"Baixa por pagamento aprovado do pedido {pedido.id}",
                pedido_id=pedido.id,
                usuario_id=usuario.id,
            )
        )


def _liberar_reservas(db: Session, pedido: Pedido, usuario: Usuario) -> None:
    for item in pedido.itens:
        estoque = estoque_repository.obter(db, pedido.unidade_id, item.produto_id, lock=True)
        if estoque is None:
            continue
        estoque_repository.liberar(estoque, item.quantidade)
        db.add(
            MovimentacaoEstoque(
                unidade_id=pedido.unidade_id,
                produto_id=item.produto_id,
                tipo=TipoMovimentacaoEstoque.LIBERACAO,
                quantidade=item.quantidade,
                motivo=f"Liberação por pagamento recusado do pedido {pedido.id}",
                pedido_id=pedido.id,
                usuario_id=usuario.id,
            )
        )


def _registrar_transicao(
    db: Session, pedido: Pedido, novo_status: StatusPedido, usuario: Usuario, observacao: str
) -> None:
    validar_transicao(pedido.status, novo_status)
    anterior = pedido.status
    pedido.status = novo_status
    db.add(
        PedidoStatusHistorico(
            pedido_id=pedido.id,
            status_anterior=anterior,
            status_novo=novo_status,
            usuario_id=usuario.id,
            observacao=observacao,
        )
    )


def _creditar_pontos(db: Session, pedido: Pedido) -> int:
    if pedido.cliente_id is None:
        return 0

    cliente = db.get(Usuario, pedido.cliente_id)
    if cliente is None or not cliente.consentimento_lgpd:
        return 0

    pontos = calcular_pontos(pedido.total)
    if pontos <= 0:
        return 0

    ja_creditado = db.scalar(
        select(PontoTransacao).where(
            PontoTransacao.pedido_id == pedido.id,
            PontoTransacao.tipo == TipoTransacaoPontos.CREDITO,
        )
    )
    if ja_creditado is not None:
        return 0

    db.add(
        PontoTransacao(
            cliente_id=cliente.id,
            pedido_id=pedido.id,
            tipo=TipoTransacaoPontos.CREDITO,
            pontos=pontos,
            descricao=f"Pontos do pedido {pedido.id}",
        )
    )
    return pontos


def processar(
    db: Session,
    *,
    pedido_id: int,
    idempotency_key: str,
    simular_resultado: str | None,
    motivo_recusa: str | None,
    usuario: Usuario,
    request_id: str | None = None,
) -> tuple[Pagamento, bool]:
    """Retorna (pagamento, criado_agora). `criado_agora=False` indica replay idempotente."""

    existente = db.scalar(
        select(Pagamento).where(Pagamento.idempotency_key == idempotency_key)
    )
    if existente is not None:
        if existente.pedido_id != pedido_id:
            raise ConflitoError(
                "Esta chave de idempotência já foi usada para outro pedido.",
                detalhes=[{"field": "Idempotency-Key", "issue": "Chave reutilizada"}],
            )
        return existente, False

    pedido = pedido_repository.obter_detalhado(db, pedido_id)
    if pedido is None:
        raise RecursoNaoEncontradoError("Pedido não encontrado.")
    _validar_acesso(pedido, usuario)

    if pedido.status is not StatusPedido.AGUARDANDO_PAGAMENTO:
        raise PedidoJaProcessadoError(
            f"O pedido está {pedido.status.value} e não aceita novo pagamento."
        )

    aprovado = _deve_aprovar(simular_resultado)
    transacao_id = f"mock_{uuid.uuid4().hex[:16]}"

    pagamento = Pagamento(
        pedido_id=pedido.id,
        status=StatusPagamento.APROVADO if aprovado else StatusPagamento.RECUSADO,
        valor=pedido.total,
        forma_pagamento=pedido.forma_pagamento,
        idempotency_key=idempotency_key,
        transacao_externa_id=transacao_id,
        motivo_recusa=None if aprovado else (motivo_recusa or "Pagamento recusado pelo emissor"),
        payload_resposta={
            "simulado": True,
            "transacaoId": transacao_id,
            "status": "APROVADO" if aprovado else "RECUSADO",
            "valor": str(pedido.total),
            "processadoEm": agora().isoformat(),
        },
        processado_em=agora(),
    )
    db.add(pagamento)
    db.flush()

    pontos = 0
    if aprovado:
        _baixar_reservas(db, pedido, usuario)
        _registrar_transicao(db, pedido, StatusPedido.PAGO, usuario, "Pagamento aprovado (mock)")
        pontos = _creditar_pontos(db, pedido)
        registrar_auditoria(
            db,
            acao="PAGAMENTO_APROVADO",
            entidade="pagamentos",
            entidade_id=pagamento.id,
            usuario_id=usuario.id,
            dados_novos={
                "pedidoId": pedido.id,
                "valor": str(pedido.total),
                "transacaoId": transacao_id,
                "pontosCreditados": pontos,
            },
            request_id=request_id,
        )
    else:
        _liberar_reservas(db, pedido, usuario)
        _registrar_transicao(
            db, pedido, StatusPedido.CANCELADO, usuario, "Pagamento recusado (mock)"
        )
        registrar_auditoria(
            db,
            acao="PAGAMENTO_RECUSADO",
            entidade="pagamentos",
            entidade_id=pagamento.id,
            usuario_id=usuario.id,
            dados_novos={
                "pedidoId": pedido.id,
                "valor": str(pedido.total),
                "motivo": pagamento.motivo_recusa,
            },
            request_id=request_id,
        )

    db.commit()
    db.refresh(pagamento)
    return pagamento, True


def listar_por_pedido(db: Session, pedido_id: int, *, usuario: Usuario) -> list[Pagamento]:
    pedido = pedido_repository.obter(db, pedido_id)
    if pedido is None:
        raise RecursoNaoEncontradoError("Pedido não encontrado.")
    _validar_acesso(pedido, usuario)
    return list(
        db.scalars(
            select(Pagamento).where(Pagamento.pedido_id == pedido_id).order_by(Pagamento.id)
        )
    )


def obter(db: Session, pagamento_id: int, *, usuario: Usuario) -> Pagamento:
    pagamento = db.get(Pagamento, pagamento_id)
    if pagamento is None:
        raise RecursoNaoEncontradoError("Pagamento não encontrado.")
    pedido = pedido_repository.obter(db, pagamento.pedido_id)
    if pedido is not None:
        _validar_acesso(pedido, usuario)
    return pagamento


def status_do_pedido(db: Session, pagamento: Pagamento) -> StatusPedido:
    pedido = pedido_repository.obter(db, pagamento.pedido_id)
    return pedido.status if pedido else StatusPedido.CANCELADO
