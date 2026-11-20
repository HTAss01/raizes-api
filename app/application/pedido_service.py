"""Casos de uso de pedidos: criação multicanal, consulta e mudança de status.

Regras centrais:
- canalPedido é obrigatório e fica gravado no pedido;
- o preço vem do cardápio da unidade e é congelado no item;
- o estoque é reservado na criação e convertido em baixa no pagamento
  aprovado; cancelamento devolve a reserva (ou o saldo, se já baixado);
- o total é sempre recalculado no servidor, nunca aceito do cliente.
"""

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.application import catalogo_service, fidelidade_service
from app.application.auditoria import registrar_auditoria
from app.domain.enums import (
    CanalPedido,
    FormaPagamento,
    PerfilUsuario,
    StatusPedido,
    TipoMovimentacaoEstoque,
    TipoTransacaoPontos,
)
from app.domain.exceptions import (
    ProdutoIndisponivelError,
    RecursoNaoEncontradoError,
    RegraNegocioError,
    SemPermissaoError,
)
from app.domain.rules.estoque import validar_disponibilidade
from app.domain.rules.fidelidade import planejar_resgate
from app.domain.rules.status_pedido import validar_permissao_transicao
from app.infrastructure.db.base import money
from app.infrastructure.db.models import (
    CardapioUnidade,
    MovimentacaoEstoque,
    Pedido,
    PedidoItem,
    PedidoStatusHistorico,
    PontoTransacao,
    Usuario,
)
from app.infrastructure.db.repositories import estoque_repository, pedido_repository


def _resolver_cliente(cliente_id: int | None, usuario: Usuario) -> int | None:
    if usuario.perfil is PerfilUsuario.CLIENTE:
        if cliente_id is not None and cliente_id != usuario.id:
            raise SemPermissaoError("Você só pode criar pedidos para o seu próprio cadastro.")
        return usuario.id
    return cliente_id


def _agregar(itens: list[tuple[int, int]]) -> dict[int, int]:
    """Soma itens repetidos: 2x produto 1 + 1x produto 1 = 3 unidades reservadas."""

    quantidades: dict[int, int] = {}
    for produto_id, quantidade in itens:
        quantidades[produto_id] = quantidades.get(produto_id, 0) + quantidade
    return quantidades


def criar_pedido(
    db: Session,
    *,
    canal_pedido: CanalPedido,
    unidade_id: int,
    itens: list[tuple[int, int]],
    forma_pagamento: FormaPagamento,
    cliente_id: int | None,
    observacao: str | None,
    usuario: Usuario,
    resgatar_pontos: bool = False,
    request_id: str | None = None,
) -> Pedido:
    if not itens:
        raise RegraNegocioError("O pedido deve conter ao menos um item.")

    catalogo_service.obter_unidade(db, unidade_id)
    cliente_resolvido = _resolver_cliente(cliente_id, usuario)
    if cliente_resolvido is not None and db.get(Usuario, cliente_resolvido) is None:
        raise RecursoNaoEncontradoError("Cliente não encontrado.")

    quantidades = _agregar(itens)

    # 1ª passada: valida tudo antes de alterar qualquer saldo.
    precos: dict[int, Decimal] = {}
    subtotal_itens = Decimal("0.00")
    for produto_id, quantidade in quantidades.items():
        produto = catalogo_service.obter_produto(db, produto_id)
        if not produto.ativo:
            raise ProdutoIndisponivelError(f"O produto {produto.nome} está desativado.")

        cardapio = db.scalar(
            select(CardapioUnidade).where(
                CardapioUnidade.unidade_id == unidade_id,
                CardapioUnidade.produto_id == produto_id,
            )
        )
        if cardapio is None:
            raise RecursoNaoEncontradoError(
                f"O produto {produto.nome} não faz parte do cardápio desta unidade."
            )
        if not cardapio.disponivel:
            raise ProdutoIndisponivelError(
                f"O produto {produto.nome} está indisponível nesta unidade."
            )

        estoque = estoque_repository.obter(db, unidade_id, produto_id, lock=True)
        if estoque is None:
            raise RecursoNaoEncontradoError(
                f"Não há estoque cadastrado para {produto.nome} nesta unidade."
            )
        validar_disponibilidade(produto_id, quantidade, estoque.disponivel)
        precos[produto_id] = cardapio.preco
        subtotal_itens += money(cardapio.preco * quantidade)

    subtotal_itens = money(subtotal_itens)
    desconto = Decimal("0.00")
    pontos_resgatados = 0

    if resgatar_pontos:
        if cliente_resolvido is None:
            raise RegraNegocioError("O resgate de pontos exige um cliente identificado.")
        cliente = db.get(Usuario, cliente_resolvido)
        if cliente is None or not cliente.consentimento_lgpd:
            raise RegraNegocioError("O resgate de pontos exige consentimento LGPD registrado.")

        pontos_resgatados, desconto = planejar_resgate(
            fidelidade_service.saldo_pontos(db, cliente.id), subtotal_itens
        )
        if pontos_resgatados == 0:
            raise RegraNegocioError(
                "Saldo de pontos insuficiente para resgate.",
                detalhes=[
                    {
                        "field": "resgatarPontos",
                        "issue": "São necessários 100 pontos para cada R$ 10,00 de desconto.",
                    }
                ],
            )

    # 2ª passada: cria o pedido, reserva o estoque e grava os itens.
    pedido = Pedido(
        cliente_id=cliente_resolvido,
        unidade_id=unidade_id,
        canal_pedido=canal_pedido,
        status=StatusPedido.AGUARDANDO_PAGAMENTO,
        forma_pagamento=forma_pagamento,
        desconto=money(desconto),
        pontos_resgatados=pontos_resgatados,
        total=money(subtotal_itens - desconto),
        observacao=observacao,
    )
    db.add(pedido)
    db.flush()

    if pontos_resgatados:
        db.add(
            PontoTransacao(
                cliente_id=cliente_resolvido,
                pedido_id=pedido.id,
                tipo=TipoTransacaoPontos.DEBITO,
                pontos=pontos_resgatados,
                descricao=f"Resgate aplicado no pedido {pedido.id}",
            )
        )

    for produto_id, quantidade in quantidades.items():
        preco = precos[produto_id]
        subtotal = money(preco * quantidade)

        estoque = estoque_repository.obter(db, unidade_id, produto_id, lock=True)
        estoque_repository.reservar(estoque, quantidade)

        db.add(
            MovimentacaoEstoque(
                unidade_id=unidade_id,
                produto_id=produto_id,
                tipo=TipoMovimentacaoEstoque.RESERVA,
                quantidade=quantidade,
                motivo=f"Reserva do pedido {pedido.id}",
                pedido_id=pedido.id,
                usuario_id=usuario.id,
            )
        )
        db.add(
            PedidoItem(
                pedido_id=pedido.id,
                produto_id=produto_id,
                quantidade=quantidade,
                preco_unitario=preco,
                subtotal=subtotal,
            )
        )

    db.add(
        PedidoStatusHistorico(
            pedido_id=pedido.id,
            status_anterior=None,
            status_novo=StatusPedido.AGUARDANDO_PAGAMENTO,
            usuario_id=usuario.id,
            observacao="Pedido criado",
        )
    )

    registrar_auditoria(
        db,
        acao="PEDIDO_CRIADO",
        entidade="pedidos",
        entidade_id=pedido.id,
        usuario_id=usuario.id,
        dados_novos={
            "canalPedido": canal_pedido.value,
            "unidadeId": unidade_id,
            "total": str(pedido.total),
            "desconto": str(pedido.desconto),
            "pontosResgatados": pedido.pontos_resgatados,
            "itens": len(quantidades),
        },
        request_id=request_id,
    )
    db.commit()

    detalhado = pedido_repository.obter_detalhado(db, pedido.id)
    return detalhado or pedido


def listar_pedidos(
    db: Session,
    *,
    usuario: Usuario,
    offset: int,
    limit: int,
    canal_pedido: CanalPedido | None = None,
    status: StatusPedido | None = None,
    unidade_id: int | None = None,
) -> tuple[list[Pedido], int]:
    """Cliente enxerga apenas os próprios pedidos; staff enxerga a rede."""

    cliente_id = usuario.id if usuario.perfil is PerfilUsuario.CLIENTE else None
    return pedido_repository.listar(
        db,
        offset=offset,
        limit=limit,
        canal_pedido=canal_pedido,
        status=status,
        unidade_id=unidade_id,
        cliente_id=cliente_id,
    )


def obter_pedido(db: Session, pedido_id: int, *, usuario: Usuario) -> Pedido:
    pedido = pedido_repository.obter_detalhado(db, pedido_id)
    if pedido is None:
        raise RecursoNaoEncontradoError("Pedido não encontrado.")
    if usuario.perfil is PerfilUsuario.CLIENTE and pedido.cliente_id != usuario.id:
        raise SemPermissaoError("Você só pode consultar os seus próprios pedidos.")
    return pedido


def _estornar_estoque(db: Session, pedido: Pedido, usuario: Usuario) -> None:
    """Devolve o saldo conforme o estágio do pedido: reserva ou baixa efetiva."""

    houve_baixa = (
        db.scalar(
            select(func.count())
            .select_from(MovimentacaoEstoque)
            .where(
                MovimentacaoEstoque.pedido_id == pedido.id,
                MovimentacaoEstoque.tipo == TipoMovimentacaoEstoque.BAIXA,
            )
        )
        or 0
    ) > 0

    for item in pedido.itens:
        estoque = estoque_repository.obter(db, pedido.unidade_id, item.produto_id, lock=True)
        if estoque is None:
            continue

        if houve_baixa:
            estoque.quantidade += item.quantidade
            tipo = TipoMovimentacaoEstoque.ENTRADA
        else:
            estoque_repository.liberar(estoque, item.quantidade)
            tipo = TipoMovimentacaoEstoque.LIBERACAO

        db.add(
            MovimentacaoEstoque(
                unidade_id=pedido.unidade_id,
                produto_id=item.produto_id,
                tipo=tipo,
                quantidade=item.quantidade,
                motivo=f"Estorno do pedido {pedido.id}",
                pedido_id=pedido.id,
                usuario_id=usuario.id,
            )
        )


def atualizar_status(
    db: Session,
    pedido_id: int,
    *,
    novo_status: StatusPedido,
    usuario: Usuario,
    observacao: str | None = None,
    request_id: str | None = None,
) -> Pedido:
    pedido = pedido_repository.obter(db, pedido_id, lock=True)
    if pedido is None:
        raise RecursoNaoEncontradoError("Pedido não encontrado.")

    if usuario.perfil is PerfilUsuario.CLIENTE and pedido.cliente_id != usuario.id:
        raise SemPermissaoError("Você só pode alterar os seus próprios pedidos.")

    validar_permissao_transicao(pedido.status, novo_status, usuario.perfil)

    status_anterior = pedido.status
    if novo_status is StatusPedido.CANCELADO:
        _estornar_estoque(db, pedido, usuario)

    pedido.status = novo_status
    db.add(
        PedidoStatusHistorico(
            pedido_id=pedido.id,
            status_anterior=status_anterior,
            status_novo=novo_status,
            usuario_id=usuario.id,
            observacao=observacao,
        )
    )
    registrar_auditoria(
        db,
        acao="PEDIDO_STATUS_ALTERADO",
        entidade="pedidos",
        entidade_id=pedido.id,
        usuario_id=usuario.id,
        dados_anteriores={"status": status_anterior.value},
        dados_novos={"status": novo_status.value, "observacao": observacao},
        request_id=request_id,
    )
    db.commit()

    detalhado = pedido_repository.obter_detalhado(db, pedido.id)
    return detalhado or pedido
