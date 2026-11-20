"""Middleware de correlação de requests.

Propaga (ou gera) um X-Request-ID por requisição, usado nos logs de
auditoria e no JSON de erro, permitindo rastrear um atendimento de ponta
a ponta entre canais.
"""

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

CABECALHO = "X-Request-ID"


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get(CABECALHO) or uuid.uuid4().hex
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers[CABECALHO] = request_id
        return response
