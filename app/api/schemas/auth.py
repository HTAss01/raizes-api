from pydantic import ConfigDict, EmailStr, Field

from app.api.schemas.base import CamelModel
from app.domain.enums import PerfilUsuario


class LoginRequest(CamelModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"email": "cliente@raizes.com.br", "senha": "Senha@123"}}
    )

    email: EmailStr = Field(description="E-mail cadastrado", examples=["cliente@raizes.com.br"])
    senha: str = Field(min_length=6, max_length=72, examples=["Senha@123"])


class RefreshRequest(CamelModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"refreshToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}}
    )

    refresh_token: str = Field(min_length=20, description="Refresh token recebido no login")


class UsuarioResumo(CamelModel):
    """Minimização de dados: não expõe hash, telefone nem consentimento."""

    id: int
    nome: str
    perfil: PerfilUsuario


class TokenResponse(CamelModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = Field(description="Validade do access token em segundos")
    user: UsuarioResumo
