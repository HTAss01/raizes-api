"""Exceções de domínio - independentes de HTTP.

Cada exceção carrega um código estável (`codigo`) usado pela camada de API
para montar o JSON padronizado de erro.
"""


class DomainError(Exception):
    """Base para toda violação de regra de negócio."""

    codigo = "ERRO_DE_NEGOCIO"
    status_code = 422
    mensagem = "Não foi possível processar a operação."

    def __init__(self, mensagem: str | None = None, detalhes: list[dict] | None = None):
        self.mensagem = mensagem or self.mensagem
        self.detalhes = detalhes or []
        super().__init__(self.mensagem)


class RecursoNaoEncontradoError(DomainError):
    codigo = "RECURSO_NAO_ENCONTRADO"
    status_code = 404
    mensagem = "Recurso não encontrado."


class CredenciaisInvalidasError(DomainError):
    codigo = "CREDENCIAIS_INVALIDAS"
    status_code = 401
    mensagem = "E-mail ou senha inválidos."


class NaoAutenticadoError(DomainError):
    codigo = "NAO_AUTENTICADO"
    status_code = 401
    mensagem = "Autenticação necessária. Envie um token Bearer válido."


class TokenInvalidoError(DomainError):
    codigo = "TOKEN_INVALIDO"
    status_code = 401
    mensagem = "Token de acesso inválido."


class TokenExpiradoError(DomainError):
    codigo = "TOKEN_EXPIRADO"
    status_code = 401
    mensagem = "Token expirado. Faça login novamente."


class SemPermissaoError(DomainError):
    codigo = "SEM_PERMISSAO"
    status_code = 403
    mensagem = "Você não tem permissão para executar esta ação."


class ConflitoError(DomainError):
    codigo = "CONFLITO"
    status_code = 409
    mensagem = "A operação conflita com o estado atual do recurso."


class EstoqueInsuficienteError(ConflitoError):
    codigo = "ESTOQUE_INSUFICIENTE"
    mensagem = "Não há quantidade suficiente para um ou mais itens."


class TransicaoStatusInvalidaError(ConflitoError):
    codigo = "TRANSICAO_STATUS_INVALIDA"
    mensagem = "A transição de status solicitada não é permitida."


class PedidoJaProcessadoError(ConflitoError):
    codigo = "PEDIDO_JA_PROCESSADO"
    mensagem = "O pedido já foi processado."


class RegraNegocioError(DomainError):
    codigo = "REGRA_DE_NEGOCIO_VIOLADA"
    status_code = 422
