"""Seed de dados iniciais (idempotente).

Uso:
    python -m app.infrastructure.db.seed

Cria: 5 perfis de usuário, 2 unidades, 8 produtos, cardápio e estoque por
unidade e 1 campanha promocional. Rodar novamente não duplica nada.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import (
    CanalPedido,
    FormaPagamento,
    PerfilUsuario,
    StatusPedido,
    TipoDescontoPromocao,
)
from app.infrastructure.db.models import (
    CardapioUnidade,
    Estoque,
    Pedido,
    PedidoItem,
    PedidoStatusHistorico,
    Produto,
    Promocao,
    Unidade,
    Usuario,
)
from app.infrastructure.db.session import get_session
from app.infrastructure.security.password import hash_senha

SENHA_PADRAO = "Senha@123"

USUARIOS = [
    ("Administrador da Rede", "admin@raizes.com.br", PerfilUsuario.ADMIN),
    ("Gerente Recife", "gerente@raizes.com.br", PerfilUsuario.GERENTE),
    ("Atendente Balcão", "atendente@raizes.com.br", PerfilUsuario.ATENDENTE),
    ("Cozinha Recife", "cozinha@raizes.com.br", PerfilUsuario.COZINHA),
    ("Maria Cliente", "cliente@raizes.com.br", PerfilUsuario.CLIENTE),
]

UNIDADES = [
    {
        "nome": "Raízes Recife - Boa Viagem",
        "cidade": "Recife",
        "uf": "PE",
        "endereco": "Av. Conselheiro Aguiar, 1500 - Boa Viagem",
        "telefone": "81 3333-1000",
    },
    {
        "nome": "Raízes Caruaru - Centro",
        "cidade": "Caruaru",
        "uf": "PE",
        "endereco": "Rua Vigário Freire, 210 - Centro",
        "telefone": "81 3722-2000",
    },
]

# (nome, categoria, preco_base, descricao)
PRODUTOS = [
    ("Coxinha de Frango", "SALGADOS", "8.50", "Massa de mandioca com frango desfiado"),
    ("Pastel de Carne de Sol", "SALGADOS", "12.00", "Pastel de feira com carne de sol e queijo coalho"),
    ("Acarajé", "SALGADOS", "15.00", "Bolinho de feijão-fradinho com vatapá e caruru"),
    ("Tapioca de Queijo Coalho", "SALGADOS", "10.00", "Tapioca fresca com queijo coalho grelhado"),
    ("Bolo de Macaxeira", "DOCES", "9.00", "Fatia de bolo de macaxeira com coco"),
    ("Cartola", "DOCES", "14.50", "Banana frita, queijo coalho e canela"),
    ("Suco de Cajá", "BEBIDAS", "7.50", "Suco natural de cajá, 400ml"),
    ("Café Coado", "BEBIDAS", "4.00", "Café coado na hora, 200ml"),
]

# estoque por unidade: (unidade_index, produto_index, quantidade, minimo)
ESTOQUES = [
    (0, 0, 50, 10),
    (0, 1, 40, 10),
    (0, 2, 30, 8),
    (0, 3, 35, 8),
    (0, 4, 25, 6),
    (0, 5, 20, 6),
    (0, 6, 60, 12),
    (0, 7, 80, 20),
    # Unidade 2 com menos estoque: Acarajé com apenas 1 unidade (cenário 409)
    (1, 0, 20, 5),
    (1, 1, 15, 5),
    (1, 2, 1, 5),
    (1, 3, 12, 4),
    (1, 4, 10, 3),
    (1, 5, 8, 3),
    (1, 6, 25, 8),
    (1, 7, 40, 10),
]


def _get_or_create_usuario(db: Session, nome: str, email: str, perfil: PerfilUsuario) -> Usuario:
    usuario = db.scalar(select(Usuario).where(Usuario.email == email))
    if usuario:
        return usuario
    usuario = Usuario(
        nome=nome,
        email=email,
        senha_hash=hash_senha(SENHA_PADRAO),
        perfil=perfil,
        ativo=True,
        consentimento_lgpd=perfil is PerfilUsuario.CLIENTE,
        consentimento_em=datetime.now(timezone.utc) if perfil is PerfilUsuario.CLIENTE else None,
    )
    db.add(usuario)
    db.flush()
    return usuario


def _get_or_create_unidade(db: Session, dados: dict) -> Unidade:
    unidade = db.scalar(select(Unidade).where(Unidade.nome == dados["nome"]))
    if unidade:
        return unidade
    unidade = Unidade(**dados)
    db.add(unidade)
    db.flush()
    return unidade


def _get_or_create_produto(db: Session, nome: str, categoria: str, preco: Decimal, descricao: str) -> Produto:
    produto = db.scalar(select(Produto).where(Produto.nome == nome))
    if produto:
        return produto
    produto = Produto(nome=nome, categoria=categoria, preco_base=preco, descricao=descricao)
    db.add(produto)
    db.flush()
    return produto


def _upsert_cardapio(db: Session, unidade: Unidade, produto: Produto, preco: Decimal, disponivel: bool) -> None:
    item = db.scalar(
        select(CardapioUnidade).where(
            CardapioUnidade.unidade_id == unidade.id,
            CardapioUnidade.produto_id == produto.id,
        )
    )
    if item:
        item.preco = preco
        item.disponivel = disponivel
        return
    db.add(CardapioUnidade(unidade_id=unidade.id, produto_id=produto.id, preco=preco, disponivel=disponivel))


def _upsert_estoque(db: Session, unidade: Unidade, produto: Produto, quantidade: int, minimo: int) -> None:
    estoque = db.scalar(
        select(Estoque).where(Estoque.unidade_id == unidade.id, Estoque.produto_id == produto.id)
    )
    if estoque:
        estoque.quantidade = quantidade
        estoque.estoque_minimo = minimo
        return
    db.add(
        Estoque(
            unidade_id=unidade.id,
            produto_id=produto.id,
            quantidade=quantidade,
            quantidade_reservada=0,
            estoque_minimo=minimo,
        )
    )


def _criar_promocao(db: Session) -> None:
    existente = db.scalar(select(Promocao).where(Promocao.nome == "Semana do Nordeste"))
    if existente:
        return
    agora = datetime.now(timezone.utc)
    db.add(
        Promocao(
            nome="Semana do Nordeste",
            descricao="10% de desconto em salgados regionais",
            tipo_desconto=TipoDescontoPromocao.PERCENTUAL,
            valor=Decimal("10.00"),
            unidade_id=None,
            produto_id=None,
            data_inicio=agora - timedelta(days=1),
            data_fim=agora + timedelta(days=30),
            ativo=True,
        )
    )


def _criar_pedido_exemplo(db: Session, cliente: Usuario, unidade: Unidade, produto: Produto) -> None:
    """Pedido demonstrativo já pago, útil para consultas na coleção Postman."""

    existente = db.scalar(select(Pedido).where(Pedido.observacao == "seed:pedido-exemplo"))
    if existente:
        return
    preco = Decimal("8.50")
    pedido = Pedido(
        cliente_id=cliente.id,
        unidade_id=unidade.id,
        canal_pedido=CanalPedido.TOTEM,
        status=StatusPedido.PAGO,
        forma_pagamento=FormaPagamento.MOCK,
        total=preco * 2,
        observacao="seed:pedido-exemplo",
    )
    db.add(pedido)
    db.flush()
    db.add(
        PedidoItem(
            pedido_id=pedido.id,
            produto_id=produto.id,
            quantidade=2,
            preco_unitario=preco,
            subtotal=preco * 2,
        )
    )
    db.add(
        PedidoStatusHistorico(
            pedido_id=pedido.id,
            status_anterior=StatusPedido.AGUARDANDO_PAGAMENTO,
            status_novo=StatusPedido.PAGO,
            usuario_id=None,
            observacao="Pagamento aprovado (seed)",
        )
    )


def run() -> None:
    db = get_session()
    try:
        usuarios = [_get_or_create_usuario(db, nome, email, perfil) for nome, email, perfil in USUARIOS]
        unidades = [_get_or_create_unidade(db, dados) for dados in UNIDADES]
        produtos = [
            _get_or_create_produto(db, nome, categoria, Decimal(preco), descricao)
            for nome, categoria, preco, descricao in PRODUTOS
        ]

        for unidade in unidades:
            for produto in produtos:
                # Unidade 2 não vende Acarajé (demonstra disponibilidade por unidade)
                indisponivel = unidade is unidades[1] and produto is produtos[2]
                _upsert_cardapio(db, unidade, produto, produto.preco_base, not indisponivel)

        for unidade_idx, produto_idx, quantidade, minimo in ESTOQUES:
            _upsert_estoque(db, unidades[unidade_idx], produtos[produto_idx], quantidade, minimo)

        _criar_promocao(db)
        _criar_pedido_exemplo(db, usuarios[-1], unidades[0], produtos[0])

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print("Seed aplicado com sucesso.")
    print(f"  usuários: {len(USUARIOS)} (senha padrão: {SENHA_PADRAO})")
    print(f"  unidades: {len(UNIDADES)}")
    print(f"  produtos: {len(PRODUTOS)}")
    print(f"  estoques: {len(ESTOQUES)}")


if __name__ == "__main__":
    run()
