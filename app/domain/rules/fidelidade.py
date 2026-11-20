"""Regras do programa de fidelização.

Política adotada (simples e auditável):
- 1 ponto por real efetivamente pago (arredondado para baixo);
- resgate em múltiplos de 100 pontos = R$ 10,00 de desconto;
- crédito apenas com consentimento LGPD registrado;
- no máximo um crédito por pedido (garantido por constraint no banco).
"""

from decimal import ROUND_DOWN, Decimal

PONTOS_POR_REAL = Decimal("1")
PONTOS_POR_RESGATE = 100
VALOR_DO_RESGATE = Decimal("10.00")


def calcular_pontos(total: Decimal) -> int:
    if total <= 0:
        return 0
    return int((total * PONTOS_POR_REAL).to_integral_value(rounding=ROUND_DOWN))


def calcular_desconto(pontos: int) -> tuple[int, Decimal]:
    """Retorna (pontos consumidos, valor do desconto)."""

    if pontos < PONTOS_POR_RESGATE:
        return 0, Decimal("0.00")
    resgates = pontos // PONTOS_POR_RESGATE
    return resgates * PONTOS_POR_RESGATE, (VALOR_DO_RESGATE * resgates).quantize(Decimal("0.01"))


def planejar_resgate(saldo_pontos: int, total_pedido: Decimal) -> tuple[int, Decimal]:
    """Resgate limitado pelo saldo e pelo valor do pedido.

    Nunca consome pontos além do necessário, e nunca gera desconto maior que
    o pedido (o troco não existe: o limite é arredondado para baixo).
    """

    if saldo_pontos < PONTOS_POR_RESGATE or total_pedido <= 0:
        return 0, Decimal("0.00")

    max_por_saldo = saldo_pontos // PONTOS_POR_RESGATE
    max_por_valor = int(total_pedido // VALOR_DO_RESGATE)
    resgates = min(max_por_saldo, max_por_valor)
    if resgates <= 0:
        return 0, Decimal("0.00")
    return resgates * PONTOS_POR_RESGATE, (VALOR_DO_RESGATE * resgates).quantize(Decimal("0.01"))
