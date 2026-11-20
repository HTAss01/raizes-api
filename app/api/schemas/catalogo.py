from decimal import Decimal

from pydantic import ConfigDict, Field, field_validator

from app.api.schemas.base import CamelModel, Money


class UnidadeBase(CamelModel):
    nome: str = Field(min_length=3, max_length=120, examples=["Raízes Recife - Boa Viagem"])
    cidade: str = Field(min_length=2, max_length=80, examples=["Recife"])
    uf: str = Field(min_length=2, max_length=2, examples=["PE"])
    endereco: str = Field(min_length=5, max_length=200)
    telefone: str | None = Field(default=None, max_length=20)

    @field_validator("uf")
    @classmethod
    def normalizar_uf(cls, valor: str) -> str:
        return valor.upper()


class UnidadeCreate(UnidadeBase):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "nome": "Raízes Olinda - Carmo",
                "cidade": "Olinda",
                "uf": "PE",
                "endereco": "Rua do Bonfim, 45 - Carmo",
                "telefone": "81 3429-3000",
            }
        }
    )


class UnidadeOut(UnidadeBase):
    id: int
    ativo: bool


class ProdutoBase(CamelModel):
    nome: str = Field(min_length=2, max_length=120, examples=["Coxinha de Frango"])
    descricao: str | None = Field(default=None, max_length=2000)
    categoria: str = Field(min_length=2, max_length=60, examples=["SALGADOS"])
    preco_base: Money = Field(ge=Decimal("0"), examples=[8.5])


class ProdutoCreate(ProdutoBase):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "nome": "Bolo de Rolo",
                "descricao": "Receita pernambucana tradicional",
                "categoria": "DOCES",
                "precoBase": 18.9,
            }
        }
    )


class ProdutoUpdate(CamelModel):
    nome: str | None = Field(default=None, min_length=2, max_length=120)
    descricao: str | None = Field(default=None, max_length=2000)
    categoria: str | None = Field(default=None, min_length=2, max_length=60)
    preco_base: Money | None = Field(default=None, ge=Decimal("0"))
    ativo: bool | None = None


class ProdutoOut(ProdutoBase):
    id: int
    ativo: bool


class CardapioItemOut(CamelModel):
    produto_id: int
    nome: str
    categoria: str
    preco: Money
    disponivel: bool
    estoque_disponivel: int


class CardapioItemUpdate(CamelModel):
    model_config = ConfigDict(json_schema_extra={"example": {"preco": 9.9, "disponivel": False}})

    preco: Money | None = Field(default=None, ge=Decimal("0"))
    disponivel: bool | None = None
