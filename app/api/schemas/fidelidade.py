from pydantic import ConfigDict

from app.api.schemas.base import CamelModel, DataHora
from app.domain.enums import TipoTransacaoPontos


class SaldoOut(CamelModel):
    cliente_id: int
    saldo_pontos: int
    valor_disponivel: float
    resgates_disponiveis: int
    pontos_para_proximo_resgate: int


class ExtratoItemOut(CamelModel):
    id: int
    tipo: TipoTransacaoPontos
    pontos: int
    descricao: str
    pedido_id: int | None
    criado_em: DataHora


class RegrasFidelidadeOut(CamelModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "pontosPorReal": 1.0,
                "pontosPorResgate": 100,
                "valorDoResgate": 10.0,
                "consentimentoObrigatorio": True,
            }
        }
    )

    pontos_por_real: float
    pontos_por_resgate: int
    valor_do_resgate: float
    consentimento_obrigatorio: bool
