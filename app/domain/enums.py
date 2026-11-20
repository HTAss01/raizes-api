"""Enums de domínio - vocabulário compartilhado entre todas as camadas."""

from enum import Enum


class PerfilUsuario(str, Enum):
    ADMIN = "ADMIN"
    GERENTE = "GERENTE"
    ATENDENTE = "ATENDENTE"
    COZINHA = "COZINHA"
    CLIENTE = "CLIENTE"


class CanalPedido(str, Enum):
    """Canal de origem do pedido (requisito de multicanalidade)."""

    APP = "APP"
    TOTEM = "TOTEM"
    BALCAO = "BALCAO"
    PICKUP = "PICKUP"
    WEB = "WEB"


class StatusPedido(str, Enum):
    AGUARDANDO_PAGAMENTO = "AGUARDANDO_PAGAMENTO"
    PAGO = "PAGO"
    EM_PREPARO = "EM_PREPARO"
    PRONTO = "PRONTO"
    ENTREGUE = "ENTREGUE"
    CANCELADO = "CANCELADO"


class StatusPagamento(str, Enum):
    PENDENTE = "PENDENTE"
    APROVADO = "APROVADO"
    RECUSADO = "RECUSADO"


class FormaPagamento(str, Enum):
    MOCK = "MOCK"
    PIX = "PIX"
    CARTAO_CREDITO = "CARTAO_CREDITO"
    CARTAO_DEBITO = "CARTAO_DEBITO"
    DINHEIRO = "DINHEIRO"


class TipoMovimentacaoEstoque(str, Enum):
    ENTRADA = "ENTRADA"
    SAIDA = "SAIDA"
    RESERVA = "RESERVA"
    LIBERACAO = "LIBERACAO"
    BAIXA = "BAIXA"


class TipoTransacaoPontos(str, Enum):
    CREDITO = "CREDITO"
    DEBITO = "DEBITO"


class TipoDescontoPromocao(str, Enum):
    PERCENTUAL = "PERCENTUAL"
    VALOR_FIXO = "VALOR_FIXO"
