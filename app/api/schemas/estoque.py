from pydantic import ConfigDict, Field, field_validator

from app.api.schemas.base import CamelModel, DataHora
from app.domain.enums import TipoMovimentacaoEstoque

TIPOS_MANUAIS = {
    TipoMovimentacaoEstoque.ENTRADA,
    TipoMovimentacaoEstoque.SAIDA,
}


class EstoqueOut(CamelModel):
    produto_id: int
    nome: str
    categoria: str
    quantidade: int
    quantidade_reservada: int
    disponivel: int = Field(description="quantidade - quantidadeReservada")
    estoque_minimo: int
    abaixo_do_minimo: bool


class MovimentacaoCreate(CamelModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "produtoId": 1,
                "tipo": "ENTRADA",
                "quantidade": 20,
                "motivo": "Reposição semanal do fornecedor",
            }
        }
    )

    produto_id: int = Field(gt=0)
    tipo: TipoMovimentacaoEstoque = Field(
        description="Apenas ENTRADA ou SAIDA podem ser lançadas manualmente",
        examples=["ENTRADA"],
    )
    quantidade: int = Field(gt=0, le=10000)
    motivo: str | None = Field(default=None, max_length=200, examples=["Compra de fornecedor"])

    @field_validator("tipo")
    @classmethod
    def validar_tipo_manual(cls, valor: TipoMovimentacaoEstoque) -> TipoMovimentacaoEstoque:
        if valor not in TIPOS_MANUAIS:
            raise ValueError("Use ENTRADA ou SAIDA; RESERVA, LIBERACAO e BAIXA são do fluxo de pedido.")
        return valor


class MovimentacaoOut(CamelModel):
    id: int
    produto_id: int
    tipo: TipoMovimentacaoEstoque
    quantidade: int
    motivo: str | None
    quantidade_apos: int
    saldo_anterior: int
    criado_em: DataHora
