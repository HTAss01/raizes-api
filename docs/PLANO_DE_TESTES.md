# Plano de Testes — Raízes API

Validação da API REST multicanal da rede **Raízes do Nordeste**, cobrindo autenticação,
autorização, validação de dados, regras de negócio do fluxo crítico, pagamento mock e
auditoria/LGPD.

## 1. Pré-requisitos

| Item | Valor |
|---|---|
| API | `uvicorn app.main:app --port 8000` |
| Banco | `alembic upgrade head` + `python -m app.infrastructure.db.seed` |
| Base URL | `http://localhost:8000` |
| Coleção | `docs/postman/Raizes-API.postman_collection.json` |
| Environment | `docs/postman/Raizes-API.postman_environment.json` |
| Credenciais | senha `Senha@123` para todos os usuários do seed |

> **Importante:** a pasta `05 - Usuários e LGPD` cadastra `joana.teste@exemplo.com` e a pasta
> `08` anonimiza essa conta. Execute a coleção completa em banco recém-semeado
> (`alembic downgrade base && alembic upgrade head && python -m app.infrastructure.db.seed`)
> para que os cenários T18, T19 e T24 sejam reproduzíveis.

## 2. Como executar

**Postman**
1. Importe a coleção e o environment.
2. Selecione o environment `Raizes API - Local`.
3. Abra **Collection Runner** → coleção completa → **Run**.
4. As variáveis (`accessToken`, `pedidoId`, `pagamentoId`, `idempotencyKey`) são preenchidas
   automaticamente pelos scripts de teste de cada requisição.

**Ordem de dependência entre pastas**

```
00 Autenticação → 01 Unidades → 02 Produtos → 03 Pedidos → 04 Pagamentos
→ 05 Usuários/LGPD → 06 Fidelidade → 07 Auditoria → 08 Direitos do titular → 09 Erros
```

Executar pastas fora de ordem quebra as variáveis encadeadas (ex.: `pedidoId`).

## 3. Cenários

### 3.1 Autenticação e autorização

| ID | Cenário | Requisição na coleção | Pré-condição | Entrada | Saída esperada |
|---|---|---|---|---|---|
| T01 | Login válido | `00 - Autenticação / Login - Cliente` | usuário do seed | `{email, senha}` | `200` + `accessToken`, `tokenType: Bearer`, `user.perfil: CLIENTE` |
| T02 | Login inválido | `00 / T02 - Login inválido` | usuário do seed | senha errada | `401` + `CREDENCIAIS_INVALIDAS` |
| T03 | Acesso sem token | `00 / T03 - Sem token` | — | sem `Authorization` | `401` + `NAO_AUTENTICADO` |
| T04 | Perfil sem permissão | `01 / T04 - Estoque sem permissão` | token de CLIENTE | `GET /unidades/{id}/estoque` | `403` + `SEM_PERMISSAO` |
| T23 | Cliente listando usuários | `05 / T23 - Cliente listando usuários` | token de CLIENTE | `GET /usuarios` | `403` + `SEM_PERMISSAO` |
| T26 | Cadastro de usuário por GERENTE | `05 / T26 - Cadastro sem permissão` | token de GERENTE | `POST /usuarios` com `perfil: ADMIN` | `403` + `SEM_PERMISSAO` |

### 3.2 Validação de dados

| ID | Cenário | Requisição na coleção | Pré-condição | Entrada | Saída esperada |
|---|---|---|---|---|---|
| T08 | Campo obrigatório ausente | `03 / T08 - Pedido sem canalPedido` | usuário autenticado | pedido sem `canalPedido` | `422` + `DADOS_INVALIDOS`, `details[].field = canalPedido` |
| T09 | Valor inválido em enum | `03 / T09 - Canal inválido` | idem | `canalPedido: "DRIVE"` | `422` + `DADOS_INVALIDOS` listando opções válidas |
| T16 | Header obrigatório ausente | `04 / T16 - Pagamento sem Idempotency-Key` | pedido existente | sem header | `422`, `details[].field = Idempotency-Key` |
| T20 | Consentimento ausente | `05 / T20 - Consentimento ausente` | token de ADMIN | cadastro sem `consentimentoLgpd` | `422`, `details[].field = consentimentoLgpd` |
| T27 | Perfil ausente no cadastro | `05 / T27 - Cadastro sem perfil` | token de ADMIN | cadastro sem `perfil` | `422`, `details[].field = perfil` |

### 3.3 Regras de negócio do fluxo principal

| ID | Cenário | Requisição na coleção | Pré-condição | Entrada | Saída esperada |
|---|---|---|---|---|---|
| T07 | Pedido criado | `03 / T01 - Criar pedido TOTEM` | seed aplicado | `{canalPedido: TOTEM, unidadeId, itens:[...]}` | `201` + `status: AGUARDANDO_PAGAMENTO`, `total > 0`, preço congelado por item |
| T10 | Estoque insuficiente | `03 / T10 - Estoque insuficiente` | produto com saldo 20 na unidade 2 | `quantidade: 999` | `409` + `ESTOQUE_INSUFICIENTE` com disponível no `details` |
| T05 | Unidade inexistente | `01 / T05 - Unidade inexistente` | — | `GET /unidades/9999` | `404` + `RECURSO_NAO_ENCONTRADO` |
| T07b | Produto inexistente | `02 / T07 - Produto inexistente` | — | `GET /produtos/9999` | `404` + `RECURSO_NAO_ENCONTRADO` |
| T11 | Filtro por canal | `03 / T11 - Filtrar por canal` | pedidos com canal TOTEM | `?canalPedido=TOTEM` | `200`, todos os itens com `canalPedido: TOTEM` |
| T12 | Transição inválida | `03 / T12 - Transição inválida (cozinha)` | pedido em `AGUARDANDO_PAGAMENTO` | `PATCH status: EM_PREPARO` com perfil COZINHA | `409` + `TRANSICAO_STATUS_INVALIDA` |
| T06 | Escrita sem permissão | `02 / T06 - Criar produto sem permissão` | token de CLIENTE | `POST /produtos` | `403` + `SEM_PERMISSAO` |

### 3.4 Pagamento mock e atualização de status

| ID | Cenário | Requisição na coleção | Pré-condição | Entrada | Saída esperada |
|---|---|---|---|---|---|
| T13 | Pagamento aprovado | `04 / T13 - Pagamento aprovado` | pedido em `AGUARDANDO_PAGAMENTO` | `simularResultado: APROVADO` + `Idempotency-Key` | `201`, `status: APROVADO`, `pedidoStatus: PAGO`, estoque baixado |
| T14 | Replay idempotente | `04 / T14 - Replay idempotente` | mesmo `Idempotency-Key` | repetição da chamada | `200`, mesmo `pagamentoId`, sem nova baixa |
| T15 | Pagamento recusado | `04 / T15 - Pagamento recusado` | pedido em `AGUARDANDO_PAGAMENTO` | `simularResultado: RECUSADO` | `201`, `status: RECUSADO`, `pedidoStatus: CANCELADO`, reserva liberada |

### 3.5 Fidelidade, LGPD e auditoria

| ID | Cenário | Requisição na coleção | Pré-condição | Entrada | Saída esperada |
|---|---|---|---|---|---|
| T17 | Resgate sem saldo | `06 / T17 - Resgate sem saldo` | cliente sem pontos | `resgatarPontos: true` | `422` + `REGRA_DE_NEGOCIO_VIOLADA` |
| T18 | Cadastro de cliente pelo ADMIN | `05 / T18 - Cadastro de cliente (ADMIN)` | token de ADMIN, banco recém-semeado | `{..., perfil: CLIENTE, consentimentoLgpd: true}` | `201`, `perfil: CLIENTE`, `consentimentoEm` preenchido, sem senha na resposta |
| T19 | E-mail duplicado | `05 / T19 - E-mail duplicado` | T18 executado, token de ADMIN | mesmo e-mail | `409` + `EMAIL_JA_CADASTRADO` |
| T21 | Portabilidade | `05 / T21 - Exportar dados pessoais` | token válido | `GET /usuarios/me/dados` | `200` com `usuario`, `pedidos`, `pontos` |
| T22 | Auditoria de ação sensível | `07 / T22 - Auditoria de pedido criado` | pedido criado (T07) | `?acao=PEDIDO_CRIADO` com token ADMIN | `200` com registro contendo `requestId` |
| T24 | Anonimização | `08 / T24 - Anonimização do titular` | cliente cadastrado em T18 | `DELETE /usuarios/me` | `204`; pedidos preservados, dados pessoais substituídos |
| T25 | Login após anonimização | `08 / T25 - Login após anonimização` | T24 executado | credenciais originais | `401` + `CREDENCIAIS_INVALIDAS` |

## 4. Cobertura exigida pelo roteiro

| Exigência | Cenários | Situação |
|---|---|---|
| Login com token válido | T01 | ✅ |
| Acesso sem token (401) | T03 | ✅ |
| Perfil sem permissão (403) | T04, T06, T23, T26 | ✅ |
| Campo obrigatório ausente (422) | T08, T16, T20, T27 | ✅ |
| Tipo/formato inválido (422) | T09 | ✅ |
| Pedido criado (201) | T07 | ✅ |
| Recurso inexistente (404) | T05, T07b | ✅ |
| Estoque insuficiente (409) | T10 | ✅ |
| Pagamento aprovado + status | T13, T14 | ✅ |
| Pagamento recusado + status | T15 | ✅ |
| Log/auditoria de ação sensível | T22 | ✅ implementado (consultável via `GET /auditoria`, ADMIN) |

**Totais:** 27 cenários numerados — **8 positivos** (2xx de fluxo esperado) e **19 negativos**
(erros e restrições). A coleção possui 61 requisições no total, incluindo passos de apoio
(logins por perfil, refresh, listagens, CRUD de produto, movimentação de estoque, dados do
titular e health check).

## 5. Evidência complementar (banco)

Para inspeção direta do log append-only:

```sql
SELECT acao, entidade, entidade_id, request_id, ip, criado_em
FROM auditoria_logs
ORDER BY id DESC
LIMIT 20;
```

Ações registradas pela aplicação: `LOGIN_SUCESSO`, `LOGIN_FALHA`, `LOGIN_BLOQUEADO`,
`TOKEN_RENOVADO`, `LOGOUT`, `USUARIO_CADASTRADO`, `USUARIO_ATUALIZADO`,
`LEITURA_DADOS_PESSOAIS`, `EXPORTACAO_DADOS_PESSOAIS`, `LGPD_ANONIMIZACAO`,
`PEDIDO_CRIADO`, `PEDIDO_STATUS_ALTERADO`, `PAGAMENTO_APROVADO`, `PAGAMENTO_RECUSADO`,
`ESTOQUE_MOVIMENTADO`, `PRODUTO_CRIADO`, `PRODUTO_ATUALIZADO`, `PRODUTO_DESATIVADO`,
`UNIDADE_CRIADA`, `CARDAPIO_ATUALIZADO`.
