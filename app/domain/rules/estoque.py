"""Regras puras de estoque por unidade."""

from app.domain.exceptions import EstoqueInsuficienteError


def validar_quantidade(quantidade: int) -> None:
    if quantidade <= 0:
        raise EstoqueInsuficienteError(
            "A quantidade deve ser maior que zero.",
            detalhes=[{"field": "quantidade", "issue": "Deve ser um inteiro positivo"}],
        )


def validar_disponibilidade(produto_id: int, solicitado: int, disponivel: int) -> None:
    """Saldo disponível = quantidade física - reservada."""

    validar_quantidade(solicitado)
    if solicitado > disponivel:
        raise EstoqueInsuficienteError(
            detalhes=[
                {
                    "field": "itens",
                    "issue": f"Produto {produto_id}: solicitado {solicitado}, disponível {disponivel}",
                }
            ]
        )
