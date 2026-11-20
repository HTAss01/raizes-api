# Diagrama de Sequência — Pedido → Pagamento Mock → Status

```mermaid
sequenceDiagram
    autonumber
    actor C as Cliente (App/Totem)
    participant API as API (FastAPI)
    participant APP as Application (casos de uso)
    participant DOM as Domain (regras)
    participant DB as Banco (SQLAlchemy)
    participant GW as Gateway Mock

    Note over C,DB: 1. Autenticação
    C->>API: POST /auth/login {email, senha}
    API->>APP: autenticar()
    APP->>DB: SELECT usuario por e-mail
    APP->>APP: verificar bcrypt + registrar LOGIN_SUCESSO
    API-->>C: 200 {accessToken, refreshToken}

    Note over C,DB: 2. Criação do pedido (reserva de estoque)
    C->>API: POST /pedidos {canalPedido, unidadeId, itens}
    API->>APP: criar_pedido()
    APP->>DOM: validar canal, cardápio e disponibilidade
    alt estoque insuficiente
        DOM-->>APP: EstoqueInsuficienteError
        API-->>C: 409 ESTOQUE_INSUFICIENTE
    else itens válidos
        APP->>DB: SELECT estoque FOR UPDATE
        APP->>DB: INSERT pedido + itens (preço congelado)
        APP->>DB: UPDATE quantidade_reservada (+)
        APP->>DB: INSERT movimentacao RESERVA + historico + auditoria PEDIDO_CRIADO
        API-->>C: 201 {status: AGUARDANDO_PAGAMENTO, total}
    end

    Note over C,GW: 3. Pagamento (idempotente)
    C->>API: POST /pagamentos {pedidoId} + Idempotency-Key
    API->>APP: processar()
    APP->>DB: SELECT pagamento por idempotency_key
    alt chave já usada
        APP-->>API: pagamento existente
        API-->>C: 200 (replay, sem nova baixa)
    else chave nova
        APP->>DB: SELECT pedido (status = AGUARDANDO_PAGAMENTO?)
        alt pedido já processado
            API-->>C: 409 PEDIDO_JA_PROCESSADO
        else
            APP->>GW: enviar solicitação (simulada)
            GW-->>APP: {transacaoId, status: APROVADO|RECUSADO}
            alt APROVADO
                APP->>DB: UPDATE estoque (- quantidade, reserva -)
                APP->>DB: INSERT movimentacao BAIXA
                APP->>DB: UPDATE pedido → PAGO + historico
                APP->>DB: INSERT pontos CREDITO (se consentimento)
                APP-->>API: pagamento APROVADO
                API-->>C: 201 {pedidoStatus: PAGO}
            else RECUSADO
                APP->>DB: UPDATE estoque (libera reserva)
                APP->>DB: UPDATE pedido → CANCELADO + historico
                APP-->>API: pagamento RECUSADO
                API-->>C: 201 {pedidoStatus: CANCELADO, motivoRecusa}
            end
        end
    end

    Note over C,DB: 4. Operação da cozinha
    C->>API: PATCH /pedidos/{id}/status {status: EM_PREPARO} (perfil COZINHA)
    API->>DOM: validar_permissao_transicao(PAGO → EM_PREPARO, COZINHA)
    alt perfil sem permissão ou transição inválida
        API-->>C: 403/409
    else permitido
        APP->>DB: UPDATE pedido + historico + auditoria PEDIDO_STATUS_ALTERADO
        API-->>C: 200 {status: EM_PREPARO}
    end
```

## Pontos de controle demonstrados

| Ponto | Como aparece no diagrama |
|---|---|
| Multicanalidade | `canalPedido` entra no passo 2 e é persistido |
| Consistência de estoque | `SELECT ... FOR UPDATE` antes de reservar/baixar |
| Idempotência | consulta por `idempotency_key` antes de qualquer efeito |
| Recusa coerente | pedido `CANCELADO` + reserva liberada, sem pontos |
| Autorização por perfil | validação da matriz de transições no passo 4 |
| Rastreabilidade | `requestId` gravado em cada `INSERT` de auditoria |
