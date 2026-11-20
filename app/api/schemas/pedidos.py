from pydantic import ConfigDict, Field

from app.api.schemas.base import CamelModel, DataHora, Money
from app.domain.enums import CanalPedido, FormaPagamento, StatusPedido


class ItemPedidoCreate(CamelModel):
    produto_id: int = Field(gt=0, examples=[1])
    quantidade: int = Field(gt=0, le=999, examples=[2])


class PedidoCreate(CamelModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "canalPedido": "TOTEM",
                "unidadeId": 1,
                "itens": [{"produtoId": 1, "quantidade": 2}, {"produtoId": 7, "quantidade": 1}],
                "formaPagamento": "MOCK",
                "observacao": "Sem cebola",
            }
        }
    )

    canal_pedido: CanalPedido = Field(
        description="Canal de origem do pedido (obrigatório, requisito de multicanalidade)",
        examples=["TOTEM"],
    )
    unidade_id: int = Field(gt=0, description="Unidade que prepara e entrega o pedido")
    itens: list[ItemPedidoCreate] = Field(min_length=1, max_length=50)
    forma_pagamento: FormaPagamento = Field(examples=["MOCK"])
    cliente_id: int | None = Field(
        default=None,
        description="Somente ATENDENTE/GERENTE/ADMIN podem informar outro cliente (venda no balcão)",
    )
    resgatar_pontos: bool = Field(
        default=False,
        description="Aplica o resgate de fidelidade: 100 pontos = R$ 10,00 de desconto",
    )
    observacao: str | None = Field(default=None, max_length=255)


class PedidoItemOut(CamelModel):
    produto_id: int
    nome: str
    quantidade: int
    preco_unitario: Money
    subtotal: Money


class PedidoOut(CamelModel):
    id: int
    cliente_id: int | None
    unidade_id: int
    canal_pedido: CanalPedido
    status: StatusPedido
    forma_pagamento: FormaPagamento
    subtotal_itens: Money
    desconto: Money
    pontos_resgatados: int
    total: Money
    observacao: str | None
    criado_em: DataHora
    atualizado_em: DataHora
    itens: list[PedidoItemOut]


class PedidoStatusUpdate(CamelModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"status": "EM_PREPARO", "observacao": "Iniciado pela cozinha"}}
    )

    status: StatusPedido
    observacao: str | None = Field(default=None, max_length=255)
