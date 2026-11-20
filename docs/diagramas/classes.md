# Diagrama de Classes (visão de domínio)

```mermaid
classDiagram
    class Usuario {
        +int id
        +str nome
        +str email
        +str senhaHash
        +PerfilUsuario perfil
        +bool ativo
        +bool consentimentoLgpd
        +datetime consentimentoEm
        +podeAutenticar() bool
    }

    class Unidade {
        +int id
        +str nome
        +str cidade
        +str uf
        +bool ativo
        +cardapioDisponivel() list
    }

    class Produto {
        +int id
        +str nome
        +str categoria
        +Decimal precoBase
        +bool ativo
    }

    class ItemCardapio {
        +int unidadeId
        +int produtoId
        +Decimal preco
        +bool disponivel
        +precoVigente() Decimal
    }

    class Estoque {
        +int unidadeId
        +int produtoId
        +int quantidade
        +int quantidadeReservada
        +int estoqueMinimo
        +disponivel() int
        +reservar(qtd)
        +liberar(qtd)
        +baixar(qtd)
    }

    class Pedido {
        +int id
        +CanalPedido canalPedido
        +StatusPedido status
        +FormaPagamento formaPagamento
        +Decimal subtotalItens
        +Decimal desconto
        +int pontosResgatados
        +Decimal total
        +adicionarItem(item)
        +podeTransicionarPara(novo) bool
        +cancelar(usuario)
    }

    class ItemPedido {
        +int produtoId
        +int quantidade
        +Decimal precoUnitario
        +Decimal subtotal
        +calcularSubtotal() Decimal
    }

    class Pagamento {
        +int id
        +StatusPagamento status
        +Decimal valor
        +str idempotencyKey
        +str transacaoExternaId
        +str motivoRecusa
        +dict payloadResposta
        +aprovar()
        +recusar(motivo)
    }

    class TransacaoPontos {
        +TipoTransacaoPontos tipo
        +int pontos
        +str descricao
    }

    class Promocao {
        +str nome
        +TipoDescontoPromocao tipoDesconto
        +Decimal valor
        +datetime dataInicio
        +datetime dataFim
        +bool ativo
        +vigenteEm(data) bool
    }

    class Auditoria {
        +str acao
        +str entidade
        +str entidadeId
        +dict dadosAnteriores
        +dict dadosNovos
        +str requestId
        +str ip
    }

    Usuario "1" --> "0..*" Pedido : realiza
    Usuario "1" --> "0..*" TransacaoPontos : acumula
    Unidade "1" --> "1..*" ItemCardapio : oferece
    Produto "1" --> "0..*" ItemCardapio : compoe
    Unidade "1" --> "0..*" Estoque : possui
    Produto "1" --> "0..*" Estoque : estocado
    Unidade "1" --> "0..*" Pedido : atende
    Pedido "1" *-- "1..*" ItemPedido : contem
    Produto "1" --> "0..*" ItemPedido : referenciado
    Pedido "1" --> "0..*" Pagamento : cobrado
    Pedido "1" --> "0..*" TransacaoPontos : origem
    Pedido --> Auditoria : gera evento
    Unidade "1" --> "0..*" Promocao : aplica
    Produto "1" --> "0..*" Promocao : aplica
```

## Máquina de estados do pedido

```mermaid
stateDiagram-v2
    [*] --> AGUARDANDO_PAGAMENTO : criar pedido (reserva estoque)
    AGUARDANDO_PAGAMENTO --> PAGO : pagamento aprovado (baixa estoque + pontos)
    AGUARDANDO_PAGAMENTO --> CANCELADO : cancelamento / pagamento recusado (libera reserva)
    PAGO --> EM_PREPARO : cozinha assume
    PAGO --> CANCELADO : gerente/admin (estorna baixa)
    EM_PREPARO --> PRONTO : cozinha finaliza
    EM_PREPARO --> CANCELADO : gerente/admin (estorna baixa)
    PRONTO --> ENTREGUE : atendente entrega
    ENTREGUE --> [*]
    CANCELADO --> [*]
```

| Transição | Perfis autorizados |
|---|---|
| `AGUARDANDO_PAGAMENTO → PAGO` | sistema (pagamento), ADMIN, GERENTE, ATENDENTE |
| `AGUARDANDO_PAGAMENTO → CANCELADO` | CLIENTE (próprio), ATENDENTE, GERENTE, ADMIN |
| `PAGO → EM_PREPARO` | COZINHA, GERENTE, ADMIN |
| `PAGO → CANCELADO` | GERENTE, ADMIN |
| `EM_PREPARO → PRONTO` | COZINHA, GERENTE, ADMIN |
| `EM_PREPARO → CANCELADO` | GERENTE, ADMIN |
| `PRONTO → ENTREGUE` | ATENDENTE, GERENTE, ADMIN |
