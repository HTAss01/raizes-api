"""Tratamento centralizado de erros - um único formato de JSON para toda a API.

Formato (contrato do roteiro):
{
  "error": "CODIGO_ESTAVEL",
  "message": "Mensagem legível",
  "details": [{"field": "...", "issue": "..."}],
  "timestamp": "2026-02-05T12:00:00Z",
  "path": "/rota",
  "requestId": "..."
}
"""

import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.domain.exceptions import DomainError

_LOCAIS_IGNORADOS = {"body", "query", "path", "header", "cookie"}

_MENSAGENS_VALIDACAO: dict[str, str] = {
    "missing": "Campo obrigatório.",
    "string_too_short": "Deve ter pelo menos {min_length} caracteres.",
    "string_too_long": "Deve ter no máximo {max_length} caracteres.",
    "string_type": "Deve ser um texto.",
    "string_pattern_mismatch": "Formato inválido.",
    "greater_than": "Deve ser maior que {gt}.",
    "greater_than_equal": "Deve ser maior ou igual a {ge}.",
    "less_than": "Deve ser menor que {lt}.",
    "less_than_equal": "Deve ser menor ou igual a {le}.",
    "int_parsing": "Deve ser um número inteiro.",
    "int_type": "Deve ser um número inteiro.",
    "float_parsing": "Deve ser um número.",
    "decimal_parsing": "Deve ser um valor numérico.",
    "bool_parsing": "Deve ser booleano (true/false).",
    "bool_type": "Deve ser booleano (true/false).",
    "dict_type": "Deve ser um objeto.",
    "list_type": "Deve ser uma lista.",
    "enum": "Valor inválido. Opções permitidas: {expected}.",
    "literal_error": "Valor inválido. Opções permitidas: {expected}.",
    "json_invalid": "Corpo da requisição não é um JSON válido.",
    "extra_forbidden": "Campo não permitido.",
}

_PREFIXO_VALUE_ERROR = "Value error, "


def _mensagem_validacao(erro: dict) -> str:
    tipo = erro.get("type", "")
    mensagem = erro.get("msg", "")
    ctx = erro.get("ctx") or {}

    if isinstance(mensagem, str) and mensagem.startswith(_PREFIXO_VALUE_ERROR):
        return mensagem[len(_PREFIXO_VALUE_ERROR):]

    if tipo == "value_error" and "email" in str(mensagem).lower():
        return "E-mail inválido."

    template = _MENSAGENS_VALIDACAO.get(tipo)
    if template is None:
        return str(mensagem)

    try:
        return template.format(**ctx)
    except (KeyError, IndexError):
        return template

_HTTP_PADRAO: dict[int, tuple[str, str]] = {
    400: ("REQUISICAO_INVALIDA", "A requisição não pôde ser interpretada."),
    401: ("NAO_AUTENTICADO", "Autenticação necessária."),
    403: ("SEM_PERMISSAO", "Você não tem permissão para executar esta ação."),
    404: ("ROTA_NAO_ENCONTRADA", "O recurso ou rota informada não existe."),
    405: ("METODO_NAO_PERMITIDO", "O método HTTP não é permitido para esta rota."),
    422: ("DADOS_INVALIDOS", "Um ou mais campos são inválidos."),
}


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or uuid.uuid4().hex


def resposta_erro(
    request: Request,
    *,
    status_code: int,
    codigo: str,
    mensagem: str,
    detalhes: list[dict] | None = None,
) -> JSONResponse:
    payload = {
        "error": codigo,
        "message": mensagem,
        "details": detalhes or [],
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "path": request.url.path,
        "requestId": _request_id(request),
    }
    return JSONResponse(
        status_code=status_code,
        content=payload,
        headers={"X-Request-ID": _request_id(request)},
    )


async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
    return resposta_erro(
        request,
        status_code=exc.status_code,
        codigo=exc.codigo,
        mensagem=exc.mensagem,
        detalhes=exc.detalhes,
    )


async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    detalhes = []
    for erro in exc.errors():
        local = ".".join(str(parte) for parte in erro.get("loc", []) if parte not in _LOCAIS_IGNORADOS)
        detalhes.append({"field": local or "body", "issue": _mensagem_validacao(erro)})
    return resposta_erro(
        request,
        status_code=422,
        codigo="DADOS_INVALIDOS",
        mensagem="Um ou mais campos são inválidos.",
        detalhes=detalhes,
    )


async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    padrao = _HTTP_PADRAO.get(exc.status_code)
    if padrao is not None:
        codigo, mensagem = padrao
    else:
        codigo, mensagem = "ERRO_HTTP", str(exc.detail or "Erro ao processar a requisição.")
    return resposta_erro(
        request,
        status_code=exc.status_code,
        codigo=codigo,
        mensagem=mensagem,
    )


async def handle_integrity_error(request: Request, exc: IntegrityError) -> JSONResponse:
    return resposta_erro(
        request,
        status_code=409,
        codigo="CONFLITO_DE_DADOS",
        mensagem="A operação viola uma restrição de integridade do banco.",
        detalhes=[{"field": "body", "issue": "Registro duplicado ou referência inexistente"}],
    )


async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    return resposta_erro(
        request,
        status_code=500,
        codigo="ERRO_INTERNO",
        mensagem="Erro interno ao processar a requisição.",
    )


def registrar_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, handle_domain_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.add_exception_handler(IntegrityError, handle_integrity_error)
    app.add_exception_handler(Exception, handle_unexpected_error)
