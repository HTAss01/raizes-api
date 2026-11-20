# Diagrama de Casos de Uso

```mermaid
flowchart LR
    cliente([Cliente\nApp / Web / Totem])
    atendente([Atendente\nBalcão])
    cozinha([Cozinha])
    gestor([Gerente / Administrador])
    gateway([Gateway de Pagamento\nMock])

    subgraph SAC["Autenticação e conta"]
        uc1(Realizar login)
        uc2(Consultar próprios dados)
        uc3(Exportar dados pessoais)
        uc4(Anonimizar conta)
        uc5(Cadastrar-se)
    end

    subgraph PED["Pedidos"]
        uc6(Realizar pedido)
        uc7(Consultar pedido)
        uc8(Acompanhar status)
        uc9(Cancelar pedido)
        uc10(Criar pedido no balcão)
    end

    subgraph PAG["Pagamento"]
        uc11(Solicitar pagamento)
        uc12(Processar pagamento - mock)
    end

    subgraph OP["Operação por unidade"]
        uc13(Consultar cardápio)
        uc14(Consultar estoque)
        uc15(Movimentar estoque)
        uc16(Gerenciar produtos)
        uc17(Ajustar cardápio da unidade)
        uc18(Cadastrar unidade)
    end

    subgraph FID["Fidelização"]
        uc19(Consultar saldo e extrato)
        uc20(Resgatar pontos no pedido)
    end

    subgraph AUD["Governança"]
        uc21(Consultar auditoria)
    end

    cliente --> uc1
    cliente --> uc5
    cliente --> uc6
    cliente --> uc7
    cliente --> uc8
    cliente --> uc9
    cliente --> uc13
    cliente --> uc19
    cliente --> uc20
    cliente --> uc2
    cliente --> uc3
    cliente --> uc4
    cliente --> uc11

    atendente --> uc1
    atendente --> uc10
    atendente --> uc8
    atendente --> uc13
    atendente --> uc15

    cozinha --> uc1
    cozinha --> uc8
    cozinha --> uc14

    gestor --> uc1
    gestor --> uc14
    gestor --> uc15
    gestor --> uc16
    gestor --> uc17
    gestor --> uc18
    gestor --> uc19
    gestor --> uc21

    uc11 --> uc12
    uc12 --> gateway
```

## UC 01 — Realizar Pedido + Solicitar Pagamento (fluxo crítico)

**Descrição:** cliente monta o pedido em um canal (App, Totem, Balcão, Pick-up ou Web),
o servidor reserva o estoque da unidade e a solicitação de pagamento é enviada ao gateway
mock, que devolve aprovação ou recusa.

**Atores:** Cliente (principal), Gateway de Pagamento (secundário — simulado).

**Pré-condições**
1. Usuário autenticado com JWT válido.
2. Unidade ativa e produto disponível no cardápio da unidade.
3. Saldo de estoque suficiente para todos os itens.

**Pós-condições**
- Sucesso: pedido em `PAGO`, estoque baixado, pontos creditados (se houver consentimento).
- Recusa: pedido em `CANCELADO`, reserva liberada, sem crédito de pontos.

**Fluxo principal**
1. Cliente envia `POST /pedidos` com `canalPedido`, `unidadeId` e itens.
2. Sistema valida canal, unidade, cardápio, produto ativo e disponibilidade de estoque.
3. Sistema congela o preço do cardápio, calcula subtotal e aplica resgate de pontos, se solicitado.
4. Sistema reserva o estoque (`RESERVA`) e cria o pedido em `AGUARDANDO_PAGAMENTO`.
5. Cliente envia `POST /pagamentos` com `Idempotency-Key`.
6. Gateway mock devolve transação aprovada.
7. Sistema converte reserva em baixa, move o pedido para `PAGO` e credita pontos.
8. Cliente consulta `GET /pedidos/{id}` e acompanha o status.

**Fluxos de exceção**
| Cenário | Resposta |
|---|---|
| `canalPedido` ausente ou inválido | `422 DADOS_INVALIDOS` |
| Unidade/produto/estoque inexistente | `404 RECURSO_NAO_ENCONTRADO` |
| Produto indisponível na unidade | `409 PRODUTO_INDISPONIVEL` |
| Estoque insuficiente | `409 ESTOQUE_INSUFICIENTE` |
| Repetição de `Idempotency-Key` | `200` com o pagamento original (sem nova baixa) |
| Pagamento recusado | `201 RECUSADO` + pedido `CANCELADO` + reserva liberada |
| Pedido já processado | `409 PEDIDO_JA_PROCESSADO` |

**Regras de negócio**
- RN1: `canalPedido` é obrigatório e rastreável em todas as consultas.
- RN2: o total é sempre calculado no servidor.
- RN3: a reserva só vira baixa com pagamento aprovado.
- RN4: idempotência garante que retry não duplica cobrança nem pontos.
- RN5: resgate exige consentimento LGPD e múltiplos de 100 pontos.
