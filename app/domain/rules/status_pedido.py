"""Máquina de estados do pedido e matriz de permissões por transição.

Fluxo crítico: AGUARDANDO_PAGAMENTO -> PAGO -> EM_PREPARO -> PRONTO -> ENTREGUE
Cancelamento permitido apenas antes da entrega, com perfis restritos.
"""

from app.domain.enums import PerfilUsuario, StatusPedido
from app.domain.exceptions import TransicaoStatusInvalidaError

TRANSICOES_PERMITIDAS: dict[StatusPedido, set[StatusPedido]] = {
    StatusPedido.AGUARDANDO_PAGAMENTO: {StatusPedido.PAGO, StatusPedido.CANCELADO},
    StatusPedido.PAGO: {StatusPedido.EM_PREPARO, StatusPedido.CANCELADO},
    StatusPedido.EM_PREPARO: {StatusPedido.PRONTO, StatusPedido.CANCELADO},
    StatusPedido.PRONTO: {StatusPedido.ENTREGUE},
    StatusPedido.ENTREGUE: set(),
    StatusPedido.CANCELADO: set(),
}

# Quem pode disparar cada transição. Transições disparadas pelo gateway de
# pagamento são executadas com perfil de sistema (None = interno).
PERMISSOES_POR_TRANSICAO: dict[tuple[StatusPedido, StatusPedido], set[PerfilUsuario]] = {
    (StatusPedido.AGUARDANDO_PAGAMENTO, StatusPedido.PAGO): {
        PerfilUsuario.ADMIN,
        PerfilUsuario.GERENTE,
        PerfilUsuario.ATENDENTE,
    },
    (StatusPedido.AGUARDANDO_PAGAMENTO, StatusPedido.CANCELADO): {
        PerfilUsuario.CLIENTE,
        PerfilUsuario.ATENDENTE,
        PerfilUsuario.GERENTE,
        PerfilUsuario.ADMIN,
    },
    (StatusPedido.PAGO, StatusPedido.EM_PREPARO): {
        PerfilUsuario.COZINHA,
        PerfilUsuario.GERENTE,
        PerfilUsuario.ADMIN,
    },
    (StatusPedido.PAGO, StatusPedido.CANCELADO): {
        PerfilUsuario.GERENTE,
        PerfilUsuario.ADMIN,
    },
    (StatusPedido.EM_PREPARO, StatusPedido.PRONTO): {
        PerfilUsuario.COZINHA,
        PerfilUsuario.GERENTE,
        PerfilUsuario.ADMIN,
    },
    (StatusPedido.EM_PREPARO, StatusPedido.CANCELADO): {
        PerfilUsuario.GERENTE,
        PerfilUsuario.ADMIN,
    },
    (StatusPedido.PRONTO, StatusPedido.ENTREGUE): {
        PerfilUsuario.ATENDENTE,
        PerfilUsuario.GERENTE,
        PerfilUsuario.ADMIN,
    },
}

# Estornos: ao cancelar um pedido já pago, o estoque reservado/baixado volta.
STATUS_COM_ESTOQUE_BAIXADO = {StatusPedido.PAGO, StatusPedido.EM_PREPARO, StatusPedido.PRONTO}


def validar_transicao(status_atual: StatusPedido, novo_status: StatusPedido) -> None:
    """Garante que a transição existe no fluxo; lança 409 caso contrário."""

    permitidos = TRANSICOES_PERMITIDAS.get(status_atual, set())
    if novo_status not in permitidos:
        raise TransicaoStatusInvalidaError(
            f"Não é possível alterar o status de {status_atual.value} para {novo_status.value}.",
            detalhes=[
                {
                    "field": "status",
                    "issue": f"Transições permitidas: {sorted(s.value for s in permitidos) or 'nenhuma'}",
                }
            ],
        )


def validar_permissao_transicao(
    status_atual: StatusPedido,
    novo_status: StatusPedido,
    perfil: PerfilUsuario | None,
) -> None:
    """Valida a matriz de permissões. `perfil=None` representa o sistema."""

    validar_transicao(status_atual, novo_status)
    if perfil is None:
        return
    permitidos = PERMISSOES_POR_TRANSICAO.get((status_atual, novo_status), set())
    if perfil not in permitidos:
        from app.domain.exceptions import SemPermissaoError

        raise SemPermissaoError(
            f"O perfil {perfil.value} não pode alterar o status de "
            f"{status_atual.value} para {novo_status.value}."
        )
