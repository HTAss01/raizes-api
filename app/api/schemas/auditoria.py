from app.api.schemas.base import CamelModel, DataHora


class AuditoriaOut(CamelModel):
    id: int
    usuario_id: int | None
    acao: str
    entidade: str
    entidade_id: str | None
    dados_novos: dict | None
    request_id: str | None
    ip: str | None
    criado_em: DataHora
