from fastapi import Request


def request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def ip_origem(request: Request) -> str | None:
    return request.client.host if request.client else None
