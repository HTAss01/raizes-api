from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.infrastructure.db.session import engine

TAGS_METADATA = [
    {"name": "Saúde", "description": "Verificação de disponibilidade da API e do banco."},
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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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
