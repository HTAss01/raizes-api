# DER — Diagrama Entidade-Relacionamento

O modelo tem 14 tabelas. Para manter legibilidade, o DER está dividido em dois recortes:
o **núcleo comercial** (pedido, cardápio, estoque e pagamento) e o **apoio operacional e
governança** (movimentações, fidelidade, promoções, histórico, auditoria e sessões).

## Núcleo comercial

```mermaid
erDiagram
    USUARIOS {
        int id PK
        string nome
        string email UK
        string senha_hash
        enum perfil
        bool ativo
        bool consentimento_lgpd
        datetime consentimento_em
    }

    UNIDADES {
        int id PK
        string nome
        string cidade
        string uf
        string endereco
        bool ativo
    }

    PRODUTOS {
        int id PK
        string nome
        string categoria
        numeric preco_base
        bool ativo
    }

    CARDAPIO_UNIDADE {
        int id PK
        int unidade_id FK
        int produto_id FK
        numeric preco
        bool disponivel
    }

    ESTOQUES {
        int id PK
        int unidade_id FK
        int produto_id FK
        int quantidade
        int quantidade_reservada
        int estoque_minimo
    }

    PEDIDOS {
        int id PK
        int cliente_id FK
        int unidade_id FK
        enum canal_pedido
        enum status
        enum forma_pagamento
        numeric desconto
        int pontos_resgatados
        numeric total
    }

    PEDIDO_ITENS {
        int id PK
        int pedido_id FK
        int produto_id FK
        int quantidade
        numeric preco_unitario
        numeric subtotal
    }

    PAGAMENTOS {
        int id PK
        int pedido_id FK
        enum status
        numeric valor
        string idempotency_key UK
        string transacao_externa_id
        string motivo_recusa
        json payload_resposta
    }

    USUARIOS ||--o{ PEDIDOS : "realiza"
    UNIDADES ||--o{ PEDIDOS : "atende"
    UNIDADES ||--o{ CARDAPIO_UNIDADE : "oferece"
    PRODUTOS ||--o{ CARDAPIO_UNIDADE : "compoe"
    UNIDADES ||--o{ ESTOQUES : "possui"
    PRODUTOS ||--o{ ESTOQUES : "estocado"
    PEDIDOS ||--|{ PEDIDO_ITENS : "contem"
    PRODUTOS ||--o{ PEDIDO_ITENS : "vendido"
    PEDIDOS ||--o{ PAGAMENTOS : "cobrado"
```

## Apoio operacional e governança

```mermaid
erDiagram
    USUARIOS {
        int id PK
        string email UK
        enum perfil
    }

    PEDIDOS {
        int id PK
        enum canal_pedido
        enum status
        numeric total
    }

    MOVIMENTACOES_ESTOQUE {
        int id PK
        int unidade_id FK
        int produto_id FK
        int pedido_id FK
        int usuario_id FK
        enum tipo
        int quantidade
        string motivo
        datetime criado_em
    }

    PEDIDO_STATUS_HISTORICO {
        int id PK
        int pedido_id FK
        int usuario_id FK
        enum status_anterior
        enum status_novo
        string observacao
        datetime criado_em
    }

    PONTOS_TRANSACOES {
        int id PK
        int cliente_id FK
        int pedido_id FK
        enum tipo
        int pontos
        string descricao
    }

    PROMOCOES {
        int id PK
        int unidade_id FK
        int produto_id FK
        string nome
        enum tipo_desconto
        numeric valor
        datetime data_inicio
        datetime data_fim
        bool ativo
    }

    AUDITORIA_LOGS {
        int id PK
        int usuario_id FK
        string acao
        string entidade
        string entidade_id
        json dados_anteriores
        json dados_novos
        string request_id
        string ip
        datetime criado_em
    }

    REFRESH_TOKENS {
        int id PK
        int usuario_id FK
        string token_hash UK
        datetime expira_em
        bool revogado
    }

    PEDIDOS ||--o{ MOVIMENTACOES_ESTOQUE : "movimenta"
    PEDIDOS ||--o{ PEDIDO_STATUS_HISTORICO : "historico"
    PEDIDOS ||--o{ PONTOS_TRANSACOES : "origem"
    USUARIOS ||--o{ MOVIMENTACOES_ESTOQUE : "lanca"
    USUARIOS ||--o{ PEDIDO_STATUS_HISTORICO : "executa"
    USUARIOS ||--o{ PONTOS_TRANSACOES : "acumula"
    USUARIOS ||--o{ AUDITORIA_LOGS : "gera"
    USUARIOS ||--o{ REFRESH_TOKENS : "autentica"
    USUARIOS ||--o{ PROMOCOES : "cria"
```

## Restrições relevantes

| Restrição | Tabela | Motivo |
|---|---|---|
| `UNIQUE(email)` | usuarios | impedir cadastro duplicado |
| `UNIQUE(unidade_id, produto_id)` | cardapio_unidade, estoques | um item por unidade |
| `CHECK(quantidade_reservada <= quantidade)` | estoques | reserva nunca maior que o saldo físico |
| `CHECK(total >= 0)` | pedidos | total líquido não negativo |
| `UNIQUE(idempotency_key)` | pagamentos | retry de pagamento não duplica cobrança |
| `UNIQUE(pedido_id, tipo)` | pontos_transacoes | um crédito e um débito por pedido |
| `CHECK(quantidade > 0)` | pedido_itens, movimentacoes_estoque | quantidade sempre positiva |
| FK com `ON DELETE CASCADE` | pedido_itens, pagamentos, pedido_status_historico, refresh_tokens | filhos não sobrevivem ao pai |
