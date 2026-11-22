from pydantic import ConfigDict, EmailStr, Field, field_validator

from app.api.schemas.base import CamelModel, DataHora, Money
from app.domain.enums import CanalPedido, PerfilUsuario, StatusPedido, TipoTransacaoPontos


class UsuarioCreate(CamelModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "nome": "João Gerente",
                "email": "joao.gerente@raizes.com.br",
                "senha": "Senha@123",
                "telefone": "81 98888-0000",
                "perfil": "GERENTE",
                "consentimentoLgpd": False,
            }
        }
    )

    nome: str = Field(min_length=3, max_length=120)
    email: EmailStr
    senha: str = Field(min_length=8, max_length=72, description="Mínimo 8 caracteres, com letras e números")
    telefone: str | None = Field(default=None, max_length=20)
    perfil: PerfilUsuario = Field(
        description=(
            "Perfil do usuário a ser criado: ADMIN, GERENTE, ATENDENTE, COZINHA ou CLIENTE. "
            "Obrigatório; somente ADMIN pode cadastrar."
        ),
        examples=["GERENTE"],
    )
    consentimento_lgpd: bool = Field(
        description=(
            "Consentimento explícito para tratamento de dados pessoais e participação "
            "no programa de fidelização. O aceite é registrado com data e hora."
        )
    )

    @field_validator("senha")
    @classmethod
    def validar_forca_senha(cls, valor: str) -> str:
        if not any(c.isalpha() for c in valor) or not any(c.isdigit() for c in valor):
            raise ValueError("A senha deve conter letras e números.")
        return valor


class UsuarioUpdateMe(CamelModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"nome": "Maria Souza Lima", "telefone": "81 98888-4321"}}
    )

    nome: str | None = Field(default=None, min_length=3, max_length=120)
    telefone: str | None = Field(default=None, max_length=20)


class UsuarioOut(CamelModel):
    """Dados do próprio titular. Nunca inclui senha ou hash.

    `email` é texto livre na saída: contas anonimizadas usam um endereço
    sintético com domínio reservado, que não passaria na validação de entrada.
    """

    id: int
    nome: str
    email: str
    telefone: str | None
    perfil: PerfilUsuario
    ativo: bool
    consentimento_lgpd: bool
    consentimento_em: DataHora | None
    criado_em: DataHora


class UsuarioListaOut(CamelModel):
    """Visão de gestão: sem dados de contato sensíveis além do necessário."""

    id: int
    nome: str
    email: str
    perfil: PerfilUsuario
    ativo: bool
    consentimento_lgpd: bool


class PedidoResumoOut(CamelModel):
    id: int
    canal_pedido: CanalPedido
    status: StatusPedido
    total: Money
    criado_em: DataHora


class PontoResumoOut(CamelModel):
    id: int
    tipo: TipoTransacaoPontos
    pontos: int
    descricao: str
    criado_em: DataHora


class ExportacaoDadosOut(CamelModel):
    """Portabilidade: todo dado pessoal tratado pela API, em um JSON."""

    gerado_em: DataHora
    usuario: UsuarioOut
    pedidos: list[PedidoResumoOut]
    pontos: list[PontoResumoOut]
