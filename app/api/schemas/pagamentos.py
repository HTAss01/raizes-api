from typing import Literal

from pydantic import ConfigDict, Field

from app.api.schemas.base import CamelModel, DataHora, Money
from app.domain.enums import FormaPagamento, StatusPagamento, StatusPedido

SimulacaoResultado = Literal["APROVADO", "RECUSADO"]


class PagamentoCreate(CamelModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"pedidoId": 1, "simularResultado": "APROVADO"},
        }
    )

    pedido_id: int = Field(gt=0)
    simular_resultado: SimulacaoResultado | None = Field(
        default=None,
        description=(
            "Força o resultado do gateway mock. Quando omitido, o resultado segue "
            "MOCK_PAYMENT_APPROVAL_RATE (aprovado por padrão)."
        ),
    )
    motivo_recusa: str | None = Field(default=None, max_length=255, examples=["Saldo insuficiente"])


class PagamentoOut(CamelModel):
    id: int
    pedido_id: int
    pedido_status: StatusPedido = Field(description="Status do pedido após o processamento")
    status: StatusPagamento
    valor: Money
    forma_pagamento: FormaPagamento
    idempotency_key: str
    transacao_externa_id: str | None
    motivo_recusa: str | None
    payload_resposta: dict | None
    criado_em: DataHora
    processado_em: DataHora | None
