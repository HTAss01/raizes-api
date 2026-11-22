# Roteiro de validação — antes de liberar para o professor

Duas etapas: **(A) teste automatizado no Postman**, que cobre tudo com asserções, e **(B) teste
manual no Swagger**, para a demonstração ao vivo. As duas partem de banco limpo.

---

## 0. Preparar o ambiente do zero

```powershell
.\.venv\Scripts\activate

# banco limpo (apaga o arquivo local do SQLite)
Remove-Item raizes.db, raizes.db-wal, raizes.db-shm -ErrorAction SilentlyContinue

# esquema + dados iniciais
alembic upgrade head
python -m app.infrastructure.db.seed

# subir a API
uvicorn app.main:app --reload --port 8000
```

Conferências rápidas:

| Verificação | Como | Esperado |
|---|---|---|
| API no ar | abrir `http://localhost:8000/health` | `{"status":"ok", ...}` |
| Swagger | abrir `http://localhost:8000/docs` | 34 operações, botão **Authorize** |
| OpenAPI | abrir `http://localhost:8000/openapi.json` | JSON com `"openapi": "3.1.0"` |

> **Importante:** os testes abaixo assumem **banco recém-semeado**. Rodar duas vezes sem reset
> faz o cenário de cadastro (T18) falhar com `409`, porque o e-mail já existe.

---

## A. Teste automatizado — Postman (recomendado)

1. Abrir o Postman → **Import** → selecionar os dois arquivos:
   - `docs/postman/Raizes-API.postman_collection.json`
   - `docs/postman/Raizes-API.postman_environment.json`
2. Selecionar o environment **Raizes API - Local** (variável `baseUrl = http://localhost:8000`).
3. Clicar nos três pontos da coleção → **Run collection**.
4. Deixar **todas** as 10 pastas marcadas e executar.

**Critério de aceite:** 59 requisições executadas, **0 falhas**. Cada requisição tem sua própria
asserção (`pm.test`), então uma falha aparece com o nome do teste e o status recebido.

Se aparecer falha, consultar a seção “Problemas comuns” no fim deste roteiro.

---

## B. Teste manual no Swagger (para a defesa)

No Swagger, os endpoints protegidos exigem token. O fluxo é sempre: **fazer login → copiar
`accessToken` → clicar em Authorize → colar o token**. Para trocar de perfil, refaça o login e
substitua o token.

### B.1 Autenticação e autorização

| # | Ação no Swagger | Resultado esperado |
|---|---|---|
| 1 | `POST /auth/login` com `{"email":"cliente@raizes.com.br","senha":"Senha@123"}` | `200`, `accessToken`, `expiresIn: 3600`, `user.perfil: CLIENTE` |
| 2 | **Authorize** → colar o token | cadeado fechado nos endpoints |
| 3 | `GET /auth/me` | `200` com `id`, `nome`, `perfil`; **sem** senha |
| 4 | `GET /usuarios` com token de CLIENTE | `403 SEM_PERMISSAO` (autorização por perfil) |
| 5 | Repetir login com `gerente@raizes.com.br` e trocar o token | `GET /usuarios` passa a retornar `200` |

### B.2 Catálogo, cardápio e estoque

| # | Ação | Resultado esperado |
|---|---|---|
| 6 | `GET /unidades` | `200`; a primeira unidade da lista é a de Caruaru (`id: 2`) |
| 7 | `GET /unidades/2/cardapio` | `200`; **Acarajé** com `disponivel: false` e `estoqueDisponivel: 1` |
| 8 | `GET /unidades/2/estoque` com token de **gerente** | `200` com `quantidade`, `quantidadeReservada`, `disponivel` |
| 9 | `GET /unidades/2/estoque` com token de **cliente** | `403 SEM_PERMISSAO` |
| 10 | `POST /unidades/2/estoque/movimentacoes` (gerente) `{"produtoId":1,"tipo":"ENTRADA","quantidade":10,"motivo":"Reposição"}` | `201`, `quantidadeApos` = anterior + 10 |
| 11 | `POST /produtos` com token de **cliente** | `403 SEM_PERMISSAO` |

### B.3 Fluxo crítico — o principal para mostrar

Com token de **cliente**:

| # | Ação | Resultado esperado |
|---|---|---|
| 12 | `POST /pedidos`<br>`{"canalPedido":"TOTEM","unidadeId":2,"itens":[{"produtoId":2,"quantidade":2},{"produtoId":7,"quantidade":1}],"formaPagamento":"MOCK"}` | `201`, `status: AGUARDANDO_PAGAMENTO`, `total: 31.5`, canal `TOTEM` |
| 13 | Anotar o `id` retornado (ex.: 2) | — |
| 14 | `GET /pedidos?canalPedido=TOTEM` | `200`; todos os itens com `canalPedido: TOTEM` |
| 15 | `GET /unidades/2/estoque` (gerente) | disponível dos produtos 2 e 7 **reduziu** (reserva) |
| 16 | `POST /pedidos` **sem** `canalPedido` | `422 DADOS_INVALIDOS` com `field: canalPedido` |
| 17 | `POST /pedidos` com `"canalPedido":"DRIVE"` | `422` listando as opções válidas |
| 18 | `POST /pedidos` `{"canalPedido":"APP","unidadeId":2,"itens":[{"produtoId":1,"quantidade":999}],"formaPagamento":"MOCK"}` | `409 ESTOQUE_INSUFICIENTE` com o saldo no `details` |

### B.4 Pagamento mock (idempotência)

| # | Ação | Resultado esperado |
|---|---|---|
| 19 | `POST /pagamentos` com header `Idempotency-Key: teste-001` e `{"pedidoId":<id>,"simularResultado":"APROVADO"}` | `201`, `status: APROVADO`, `pedidoStatus: PAGO`, `transacaoExternaId: mock_...` |
| 20 | Repetir **a mesma chave** | `200`, **mesmo** `id` de pagamento — não baixa estoque de novo |
| 21 | `POST /pagamentos` com chave nova para o mesmo pedido | `409 PEDIDO_JA_PROCESSADO` |
| 22 | `POST /pagamentos` sem o header | `422`, `field: Idempotency-Key` |
| 23 | `GET /pedidos/<id>` | `status: PAGO`, itens com `precoUnitario` congelado |

### B.5 Máquina de estados e perfis

| # | Ação | Resultado esperado |
|---|---|---|
| 24 | Login **cozinha** → `PATCH /pedidos/<id>/status` `{"status":"EM_PREPARO"}` | `200` (o pedido está em `PAGO`) |
| 25 | Login **cliente** → `PATCH /pedidos/<id>/status` `{"status":"PRONTO"}` | `403` (cliente não move produção) |
| 26 | Login **atendente** → `PATCH` `{"status":"ENTREGUE"}` com o pedido em `PRONTO` | `200` |
| 27 | Novo pedido + `POST /pagamentos` com `"simularResultado":"RECUSADO"` | `201 RECUSADO`, `pedidoStatus: CANCELADO`; estoque liberado |
| 28 | `PATCH /pedidos/<cancelado>/status` `{"status":"ENTREGUE"}` | `409 TRANSICAO_STATUS_INVALIDA` |

### B.6 Fidelidade, LGPD e auditoria

| # | Ação | Resultado esperado |
|---|---|---|
| 29 | `GET /fidelidade/saldo` (cliente do pedido pago) | `200`; pontos = parte inteira do total pago |
| 30 | `GET /fidelidade/extrato` | `200` com `CREDITO` do pedido pago |
| 31 | `GET /fidelidade/regras` | `200`; 100 pontos = R$ 10,00 |
| 32 | `POST /pedidos` com `"resgatarPontos":true` em cliente sem saldo | `422 REGRA_DE_NEGOCIO_VIOLADA` |
| 33 | `POST /usuarios` `{"nome":"Teste Demo","email":"demo@exemplo.com","senha":"Segura123","consentimentoLgpd":true}` | `201`, perfil CLIENTE, `consentimentoEm` preenchido |
| 34 | `GET /usuarios/me/dados` com token desse cliente | `200` com `usuario`, `pedidos`, `pontos` |
| 35 | `DELETE /usuarios/me` | `204`; o token deixa de valer (`401` nas próximas chamadas) |
| 36 | Login **admin** → `GET /auditoria?acao=PEDIDO_CRIADO` | `200` com registros contendo `requestId` |
| 37 | `GET /auditoria` com token de cliente | `403 SEM_PERMISSAO` |

---

## C. Checklist de aceite antes de entregar

- [ ] `GET /health` responde `ok`
- [ ] `/docs` abre com 34 operações e o Authorize funciona
- [ ] Coleção completa no Runner: **59 requisições, 0 falhas**
- [ ] Pedido criado com canal, reserva reduzindo estoque e pagamento mudando status para `PAGO`
- [ ] Recusa de pagamento cancela o pedido e libera a reserva
- [ ] `401`, `403`, `404`, `409` e `422` aparecem com o JSON padronizado (com `requestId`)
- [ ] `GET /auditoria` mostra `PEDIDO_CRIADO` e `PAGAMENTO_APROVADO`
- [ ] README confere com o que você executou (comandos, porta, credenciais)
- [ ] Repositório, Swagger e coleção acessíveis por link público
- [ ] PDF final na pasta do trabalho

---

## D. Problemas comuns

| Sintoma | Causa provável | Solução |
|---|---|---|
| `409 EMAIL_JA_CADASTRADO` no cenário de cadastro | coleção rodada duas vezes no mesmo banco | apagar `raizes.db*`, `alembic upgrade head`, `seed`, rodar de novo |
| `401 NAO_AUTENTICADO` em tudo | token não colado no Authorize ou expirado (60 min) | refazer login e recolar |
| `403 SEM_PERMISSAO` em estoque/produtos | token de CLIENTE | logar como gerente/admin |
| `409 ESTOQUE_INSUFICIENTE` em pedido pequeno | estoque já consumido por testes anteriores | resetar o banco |
| `500` ao subir a API | banco sem migrations | `alembic upgrade head` |
| `Address already in use` na porta 8000 | instância anterior rodando | fechar o processo ou usar `--port 8001` (e ajustar `baseUrl`) |
| Coleção falha na pasta 03 | `pedidoId` vazio: pasta 00 não rodou | executar a coleção inteira, na ordem |
| Pedido falha com `PRODUTO_INDISPONIVEL` | Acarajé está indisponível na unidade 2 (de propósito) | usar outro produto ou a unidade 1 |
