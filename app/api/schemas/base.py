from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, PlainSerializer
from pydantic.alias_generators import to_camel

T = TypeVar("T")

# Dinheiro: Decimal no domínio, número com 2 casas no JSON.
Money = Annotated[
    Decimal,
    PlainSerializer(lambda valor: float(round(valor, 2)), return_type=float, when_used="json"),
]


def _iso_utc_z(valor: datetime) -> str:
    """Datas sempre em UTC e com sufixo Z, como no contrato de erro."""

    if valor.tzinfo is None:
        valor = valor.replace(tzinfo=timezone.utc)
    return valor.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


DataHora = Annotated[datetime, PlainSerializer(_iso_utc_z, return_type=str, when_used="json")]


class CamelModel(BaseModel):
    """Base dos schemas: Python em snake_case, JSON em camelCase."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        str_strip_whitespace=True,
    )


class MetaPaginacao(CamelModel):
    page: int
    limit: int
    total: int
    total_pages: int


class Pagina(CamelModel, Generic[T]):
    """Envelope padrão de listagem paginada."""

    data: list[T]
    meta: MetaPaginacao
