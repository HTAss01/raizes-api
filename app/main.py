from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.errors import registrar_handlers
from app.api.middleware import RequestIdMiddleware
from app.api.routers import (
    auth,
    fidelidade,
    pagamentos,
    pedidos,
    produtos,
    unidades,
    usuarios,
)
from app.api.routers import auditoria as auditoria_routes
from app.config import settings
from app.infrastructure.db.session import engine

TAGS_METADATA = [
    {"name": "Saúde", "description": "Verificação de disponibilidade da API e do banco."},
    {
        "name": "Autenticação",
        "description": "Login, renovação e revogação de tokens, dados do usuário autenticado.",
    },
    {
        "name": "Unidades",
        "description": "Unidades da rede, cardápio por unidade e estoque operacional.",
    },
    {"name": "Produtos", "description": "Catálogo de produtos da rede (CRUD com exclusão lógica)."},
    {
        "name": "Usuários",
        "description": "Cadastro de usuários por ADMIN (com perfil) e dados do titular.",
    },
    {
        "name": "Pedidos",
        "description": "Pedido multicanal (canalPedido), reserva de estoque e máquina de estados.",
    },
    {
        "name": "Pagamentos",
        "description": "Pagamento simulado (mock) com idempotência, aprovação e recusa.",
    },
    {
        "name": "Fidelidade",
        "description": "Saldo, extrato e regras do programa de pontos (resgate no pedido).",
    },
    {
        "name": "Auditoria",
        "description": "Consulta do log append-only de ações sensíveis (somente ADMIN).",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "API REST multicanal da rede **Raízes do Nordeste**.\n\n"
            "Fluxo crítico: Pedido → Pagamento (mock) → Atualização de status.\n\n"
            "Autenticação via JWT (Bearer). Perfis: ADMIN, GERENTE, ATENDENTE, COZINHA, CLIENTE."
        ),
        openapi_tags=TAGS_METADATA,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    registrar_handlers(app)

    app.include_router(auth.router)
    app.include_router(usuarios.router)
    app.include_router(unidades.router)
    app.include_router(produtos.router)
    app.include_router(pedidos.router)
    app.include_router(pagamentos.router)
    app.include_router(fidelidade.router)
    app.include_router(auditoria_routes.router)

    @app.get("/health", tags=["Saúde"], summary="Verifica API e conexão com o banco")
    def health() -> dict:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "app": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
        }

    return app


app = create_app()
