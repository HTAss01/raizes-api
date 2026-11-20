"""Hash e verificação de senha (bcrypt via passlib).

Senha nunca é armazenada em texto puro e nunca retorna em responses.
"""

from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_senha(senha: str) -> str:
    return _pwd_context.hash(senha)


def verificar_senha(senha: str, senha_hash: str) -> bool:
    try:
        return _pwd_context.verify(senha, senha_hash)
    except ValueError:
        return False
