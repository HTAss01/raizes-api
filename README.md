# Raízes API

> API REST multicanal para a rede de franquias Raízes do Nordeste: pedidos, estoque por unidade, fidelização e pagamento desacoplado (mock).

Atividade Prática — **Projeto Multidisciplinar (Eletiva IV)** — Trilha **Back-End**.

---

## Sobre o projeto

A **Raízes do Nordeste** é uma rede de lanchonetes nordestinas em expansão, presente em diferentes
capitais e cidades do interior. Com o crescimento, a operação passou a exigir um sistema capaz de
atender o mesmo pedido por múltiplos canais — **App, Totem, Balcão, Pick-up e Web** — respeitando as
diferenças de cardápio e estoque de cada unidade, sem perder rastreabilidade, segurança e
conformidade com a LGPD.

Esta API é o back-end dessa solução.

### Escopo do MVP

- Autenticação com JWT e autorização por perfis (roles)
- Cadastro de cliente com consentimento LGPD registrado
- Cardápio e estoque por unidade
- Criação de pedido com registro obrigatório do canal de origem (`canalPedido`) e filtro por canal
- Fluxo crítico: **Pedido → Pagamento (mock) → Atualização de status**
- Reserva de estoque na criação, baixa no pagamento aprovado e liberação na recusa
- Programa de fidelização (acúmulo, saldo, extrato e resgate no pedido)
- Logs de auditoria de ações sensíveis, consultáveis por ADMIN
- LGPD: consentimento, portabilidade e anonimização
- Documentação via Swagger/OpenAPI

## Stack

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.11+ |
| Framework | FastAPI |
| Validação | Pydantic v2 |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic |
| Banco de dados | SQLite (portável para PostgreSQL) |
| Autenticação | JWT (PyJWT) + bcrypt (passlib) |
| Documentação | Swagger / OpenAPI (nativo do FastAPI) |
| Testes de API | Postman |

## Arquitetura

Organização em camadas, com separação clara de responsabilidades:

```
app/
├── domain/                  # Núcleo: não conhece FastAPI nem SQLAlchemy
│   ├── enums.py             # Perfis, canais, status, tipos de movimentação
│   ├── exceptions.py        # Exceções de negócio com código e status HTTP
│   └── rules/               # Regras puras (testáveis sem banco)
│       ├── status_pedido.py # Máquina de estados + matriz de permissões
│       ├── estoque.py       # Disponibilidade = quantidade - reservada
│       └── fidelidade.py    # Pontuação e resgate
├── application/             # Casos de uso (orquestração de transações)
│   ├── auth_service.py      # Login, refresh rotativo, logout
│   ├── usuario_service.py   # Cadastro, dados do titular, anonimização LGPD
│   ├── catalogo_service.py  # Unidades, produtos, cardápio por unidade
│   ├── estoque_service.py   # Entrada/saída por unidade
│   ├── pedido_service.py    # Criação multicanal, reserva, máquina de estados
│   ├── pagamento_service.py # Pagamento mock idempotente + baixa/liberação
│   ├── fidelidade_service.py# Saldo, extrato e regras de pontos
│   └── auditoria.py         # Log append-only de ações sensíveis
├── infrastructure/          # Detalhes técnicos substituíveis
│   ├── db/
│   │   ├── base.py          # Base declarativa + convenção de constraints
│   │   ├── session.py       # Engine, sessão e dependência get_db
│   │   ├── models.py        # 14 modelos ORM (DER)
│   │   ├── seed.py          # Dados iniciais idempotentes
│   │   └── repositories/    # Acesso a dados com lock (estoque, pedidos)
│   └── security/
│       ├── password.py      # Hash bcrypt
│       └── tokens.py        # JWT + refresh token com hash SHA-256
└── api/                     # Routers, schemas Pydantic e dependências
    ├── errors.py            # Handler único de erros (contrato padronizado)
    ├── middleware.py        # X-Request-ID
    ├── deps.py              # get_current_user, require_perfis, paginação
    ├── contexto.py          # request_id e IP de origem
    ├── schemas/             # Contratos request/response (camelCase)
    └── routers/             # auth, usuarios, unidades, produtos, pedidos,
                             # pagamentos, fidelidade, auditoria
```

Dependência aponta sempre para dentro: `api → application → domain`,
`infrastructure` implementa o que o domínio/aplicação precisam.

### Artefatos de documentação

| Artefato | Caminho |
|---|---|
| Relatório final (PDF, ABNT) | `docs/relatorio/4992316_Projeto_Back_End.pdf` |
| Texto do relatório | `docs/relatorio/RELATORIO.md` |
| DER (entidade-relacionamento) | `docs/diagramas/der.md` (+ PNG/SVG em `docs/diagramas/img/`) |
| Casos de uso + descrição do fluxo crítico | `docs/diagramas/casos-de-uso.md` |
| Diagrama de classes e máquina de estados | `docs/diagramas/classes.md` |
| Sequência Pedido → Pagamento → Status | `docs/diagramas/sequencia-pedido-pagamento.md` |
| Plano de testes (27 cenários) | `docs/PLANO_DE_TESTES.md` |
| Coleção Postman | `docs/postman/Raizes-API.postman_collection.json` |
| Environment Postman | `docs/postman/Raizes-API.postman_environment.json` |

## Como executar

Pré-requisitos: **Python 3.11+** (testado em 3.12) e Git. Não precisa de Docker:
o banco padrão é SQLite.

```bash
# 1. Clonar
git clone git@github.com:HTAss01/raizes-api.git
cd raizes-api

# 2. Ambiente virtual
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

# 3. Dependências
pip install -r requirements.txt

# 4. Variáveis de ambiente
cp .env.example .env      # Windows: copy .env.example .env

# 5. Banco + migrations
alembic upgrade head

# 6. Dados iniciais
python -m app.infrastructure.db.seed

# 7. Subir a API
uvicorn app.main:app --reload --port 8000
```

Acesse:
- Swagger UI: http://localhost:8000/docs
- OpenAPI JSON: http://localhost:8000/openapi.json
- Health check: http://localhost:8000/health

### Credenciais do seed

Todos os usuários usam a senha `Senha@123`.

| Perfil | E-mail |
|---|---|
| ADMIN | admin@raizes.com.br |
| GERENTE | gerente@raizes.com.br |
| ATENDENTE | atendente@raizes.com.br |
| COZINHA | cozinha@raizes.com.br |
| CLIENTE | cliente@raizes.com.br |

### Primeiro acesso (ADMIN)

Como `POST /usuarios` exige um ADMIN, o **primeiro administrador é criado pelo seed** — não existe
endpoint público que crie contas, justamente para evitar escalada de privilégio. O fluxo inicial é:

1. `POST /auth/login` com `{ "email": "admin@raizes.com.br", "senha": "Senha@123" }`;
2. copiar o `accessToken` e aplicar em **Authorize** no Swagger (o botão se encontra ao topo da página no canto direito inferior do cabeçalho);
<img width="1298" height="302" alt="image" src="https://github.com/user-attachments/assets/f91f543d-d3d4-4ec5-92e2-53db9a0a6f2d" />

3. a partir daí, cadastrar os demais usuários com `POST /usuarios` e o campo `perfil`
   (`GERENTE`, `ATENDENTE`, `COZINHA`, `CLIENTE` ou outro `ADMIN`).

Se o banco for recriado, o admin volta com o seed. Para trocar a senha inicial, altere
`SENHA_PADRAO` em `app/infrastructure/db/seed.py` antes de rodar o seed.

### PostgreSQL (opcional)

Basta trocar uma linha no `.env` — nenhum código muda:

```env
DATABASE_URL=postgresql+psycopg://raizes:raizes@localhost:5432/raizes
```

Depois: `alembic upgrade head` e `python -m app.infrastructure.db.seed`.

## Documentação da API (Swagger)

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI JSON:** http://localhost:8000/openapi.json

A especificação é **gerada a partir do código** (schemas Pydantic + anotações dos routers),
portanto não existe contrato escrito à mão que possa divergir da implementação.

### Autenticar no Swagger

1. Execute `POST /auth/login` com um dos usuários do seed.
2. Copie **apenas o valor** de `accessToken` (começa com `eyJ`; ~240 caracteres).
3. Clique em **Authorize** (canto superior direito), cole o valor, confirme em **Authorize** e
   feche a caixa em **Close**.
4. Os cadeados dos endpoints protegidos passam a aparecer fechados.

Detalhes que evitam erro comum:

- o bloco **Parameters** não lista o token: Bearer é esquema de segurança, representado pelo cadeado;
- não cole o `refreshToken` no Authorize — ele só é aceito em `POST /auth/refresh`;
- não digite `Bearer` junto do token; o Swagger acrescenta o prefixo;
- o token expira em 60 minutos; depois disso, refaça o login;
- para testar outro perfil, faça login com outro usuário e repita o passo 3;
- para conferir **com qual perfil você está logado**, use `GET /auth/me`: o campo `perfil` da
  resposta é a sua sessão real — o exemplo de schema mostrado pelo Swagger não representa você.

### Endpoints por recurso

| Recurso | Endpoint | Autenticação / perfil |
|---|---|---|
| Autenticação | `POST /auth/login` | público |
| | `POST /auth/refresh`, `POST /auth/logout` | público (exige refresh token) |
| | `GET /auth/me` | JWT |
| Usuários | `POST /usuarios` | **ADMIN** (o `perfil` é obrigatório no corpo) |
| | `GET /usuarios/me`, `PATCH /usuarios/me` | JWT (próprio titular) |
| | `GET /usuarios/me/dados` (portabilidade) | JWT (próprio titular) |
| | `DELETE /usuarios/me` (anonimização) | JWT (próprio titular) |
| | `GET /usuarios` | ADMIN, GERENTE |
| Unidades | `GET /unidades`, `GET /unidades/{id}` | JWT |
| | `POST /unidades` | ADMIN, GERENTE |
| | `GET /unidades/{id}/cardapio` | JWT |
| | `PUT /unidades/{id}/cardapio/{produtoId}` | ADMIN, GERENTE |
| | `GET /unidades/{id}/estoque` | ADMIN, GERENTE, ATENDENTE, COZINHA |
| | `POST /unidades/{id}/estoque/movimentacoes` | ADMIN, GERENTE |
| Produtos | `GET /produtos`, `GET /produtos/{id}` | JWT |
| | `POST /produtos`, `PATCH /produtos/{id}`, `DELETE /produtos/{id}` | ADMIN, GERENTE |
| Pedidos | `POST /pedidos` | JWT (CLIENTE cria para si) |
| | `GET /pedidos` (`?canalPedido=`, `?status=`, `?unidadeId=`) | JWT (CLIENTE vê só os seus) |
| | `GET /pedidos/{id}` | dono ou staff |
| | `PATCH /pedidos/{id}/status` | conforme matriz de transições |
| | `GET /pedidos/{id}/pagamentos` | dono ou staff |
| Pagamentos | `POST /pagamentos` (header `Idempotency-Key` obrigatório) | JWT (dono do pedido) |
| | `GET /pagamentos/{id}` | dono ou staff |
| Fidelidade | `GET /fidelidade/saldo`, `GET /fidelidade/extrato`, `GET /fidelidade/regras` | JWT |
| Auditoria | `GET /auditoria` (`?acao=`, `?entidade=`, `?entidadeId=`) | ADMIN |
| Saúde | `GET /health` | público |

### Cadastro de usuários e perfis

O `POST /usuarios` é **protegido**: exige token de um usuário com perfil **ADMIN** e o campo
`perfil` é **obrigatório** no corpo.

| Quem chama | `perfil` no corpo | Resultado |
|---|---|---|
| sem token | qualquer | `401 NAO_AUTENTICADO` |
| ADMIN autenticado | `ADMIN`, `GERENTE`, `ATENDENTE`, `COZINHA` ou `CLIENTE` | `201` com o perfil informado |
| GERENTE, ATENDENTE, COZINHA ou CLIENTE | qualquer | `403 SEM_PERMISSAO` |
| ADMIN autenticado | ausente | `422 DADOS_INVALIDOS` (`field: perfil`) |

Exemplo de criação de gerente (login como `admin@raizes.com.br`, token no **Authorize**):

```json
{
  "nome": "João Gerente",
  "email": "joao.gerente@raizes.com.br",
  "senha": "Senha@123",
  "perfil": "GERENTE",
  "consentimentoLgpd": false
}
```

Perfis aceitos: `ADMIN`, `GERENTE`, `ATENDENTE`, `COZINHA`, `CLIENTE`. A criação nunca é anônima:
um endpoint público jamais pode aceitar que o próprio usuário se declare administrador.

### Padrão de erro (igual em toda a API)

```json
{
  "error": "ESTOQUE_INSUFICIENTE",
  "message": "Não há quantidade suficiente para um ou mais itens.",
  "details": [{ "field": "itens", "issue": "Produto 1: solicitado 999, disponível 20" }],
  "timestamp": "2026-02-05T12:00:00Z",
  "path": "/pedidos",
  "requestId": "3f1c0a7d9e2b4c5f8a6d1e2f3a4b5c6d"
}
```

- `requestId` também vai no header `X-Request-ID` (aceita o valor enviado pelo cliente).
- Mensagens de validação são traduzidas para PT-BR; nenhum texto do validador vaza.
- Status utilizados: `200`, `201`, `204`, `401`, `403`, `404`, `409`, `422`, `500`.

## Regras de negócio principais

| Regra | Implementação |
|---|---|
| `canalPedido` obrigatório (multicanalidade) | enum validado no schema; grava no pedido; filtro `?canalPedido=` |
| Total calculado no servidor | preço vem de `cardapio_unidade` e é congelado em `pedido_itens` |
| Reserva → baixa de estoque | `RESERVA` na criação, `BAIXA` no pagamento aprovado, `LIBERACAO` na recusa/cancelamento |
| Estoque insuficiente | `409 ESTOQUE_INSUFICIENTE` com saldo disponível no `details` |
| Máquina de estados | matriz `AGUARDANDO_PAGAMENTO→PAGO→EM_PREPARO→PRONTO→ENTREGUE` + `CANCELADO` |
| Autorização por transição | COZINHA só prepara/pronto; ATENDENTE só entrega; GERENTE/ADMIN cancelam |
| Idempotência de pagamento | `Idempotency-Key` único; replay devolve `200` com o mesmo pagamento |
| Fidelidade | 1 ponto por real pago; 100 pontos = R$ 10,00; crédito único por pedido |
| Resgate | aplicado na criação do pedido (`resgatarPontos`), limitado por saldo e pelo total |

## Pagamento mock

O gateway é simulado internamente (`app/application/pagamento_service.py`):

- `POST /pagamentos` recebe `{ "pedidoId": 1, "simularResultado": "APROVADO" }`;
- `simularResultado` (`APROVADO` | `RECUSADO`) existe para tornar os testes determinísticos;
  sem ele, vale `MOCK_PAYMENT_APPROVAL_RATE` do `.env` (100 = sempre aprova);
- a resposta simulada é persistida em `pagamentos.payload_resposta` (transação, status, valor),
  comprovando o "envio e retorno" sem depender de provedor real;
- aprovação: baixa estoque, `PAGO`, crédito de pontos;
- recusa: libera a reserva, `CANCELADO`, sem pontos.

## Promoções e campanhas

Modelada em `promocoes` (seed cria "Semana do Nordeste": 10% em salgados, vigência de 30 dias)
com escopo opcional por unidade e/ou produto, tipo `PERCENTUAL` ou `VALOR_FIXO`, `data_inicio`,
`data_fim` e `ativo`.

**Regra de aplicação (documentada, não aplicada ao total nesta versão):**

```text
desconto = 0
para cada promoção ativa onde (unidade_id is NULL ou = pedido.unidade_id)
                          e (produto_id is NULL ou = item.produto_id)
                          e data_inicio <= agora <= data_fim:
    se tipo = PERCENTUAL: desconto += item.subtotal * valor / 100
    se tipo = VALOR_FIXO: desconto += valor * item.quantidade
total = max(0, subtotal_itens - desconto_fidelidade - desconto_promocao)
```

Decisão de escopo: como o roteiro aceita promoções "ao menos como regra/documentação",
o MVP priorizou o fluxo crítico (pedido → pagamento → status) e a fidelidade; a tabela e o
seed existem para que a regra acima seja implementada sem alterar o DER.

## Testes

- **Coleção:** `docs/postman/Raizes-API.postman_collection.json` (10 pastas, 61 requisições)
- **Environment:** `docs/postman/Raizes-API.postman_environment.json`
- **Plano com os 27 cenários:** `docs/PLANO_DE_TESTES.md`
- **Roteiro passo a passo (manual e automatizado):** `docs/ROTEIRO_DE_VALIDACAO.md`

### Preparar o banco

Os cenários de cadastro e de estoque dependem de dados limpos. Antes de uma bateria completa:

```bash
alembic upgrade head
python -m app.infrastructure.db.seed
```

Se já houver `raizes.db` de uma execução anterior, apague o arquivo (e os `.db-wal` / `.db-shm`)
antes dos dois comandos.

### Teste automatizado (recomendado)

1. Suba a API em `http://localhost:8000` com banco migrado e seed aplicado.
2. Importe coleção + environment no Postman e selecione o environment `Raizes API - Local`.
3. **Collection Runner** → Run, com as 10 pastas marcadas.
4. Resultado esperado: **61 requisições, 0 falhas**.

Ordem das pastas (é a dependência entre elas):

```
00 Autenticação → 01 Unidades e cardápio → 02 Produtos → 03 Pedidos
→ 04 Pagamentos → 05 Usuários e LGPD → 06 Fidelidade → 07 Auditoria
→ 08 Direitos do titular → 09 Erros e saúde
```

As variáveis (`accessToken`, `pedidoId`, `pagamentoId`, `idempotencyKey`) são encadeadas pelas
próprias requisições; não é preciso preencher nada à mão.

### Teste manual no Swagger

O roteiro completo está em `docs/ROTEIRO_DE_VALIDACAO.md`. Ordem sugerida:

1. login do cliente e **Authorize** (ver seção anterior);
2. `GET /auth/me` (200) e `GET /usuarios` (403, autorização por perfil);
3. `GET /unidades` e `GET /unidades/{id}/cardapio`;
4. `GET /unidades/{id}/estoque` com gerente (200) e com cliente (403);
5. `POST /pedidos` com `canalPedido: TOTEM` (201, total calculado);
6. `POST /pagamentos` com `Idempotency-Key` (201, pedido `PAGO`) e repetição da mesma chave (200);
7. `PATCH /pedidos/{id}/status` com cozinha e atendente; transição proibida devolve 409;
8. `GET /fidelidade/saldo`, `GET /usuarios/me/dados` e `GET /auditoria` (token de ADMIN).

### Problemas comuns

| Sintoma | Causa provável | Solução |
|---|---|---|
| `401 NAO_AUTENTICADO` em endpoints protegidos | token não aplicado no Authorize, ou expirado | refazer login e repetir o passo 3 do Authorize |
| `401 TOKEN_INVALIDO` | foi colado o `refreshToken` em vez do `accessToken` | copiar o campo `accessToken` |
| `409 EMAIL_JA_CADASTRADO` no cenário de cadastro | coleção executada duas vezes no mesmo banco | apagar `raizes.db*`, migrar, semear e rodar de novo |
| `403 SEM_PERMISSAO` em estoque ou produtos | token de CLIENTE | logar como gerente ou admin |
| `409 ESTOQUE_INSUFICIENTE` em pedido pequeno | estoque consumido por execução anterior | resetar o banco |
| `422` com `field: canalPedido` | campo ausente no corpo do pedido | incluir `canalPedido` |

Cobertura: login (200), sem token (401), perfil sem permissão (403), validação (422),
recurso inexistente (404), estoque insuficiente (409), transição inválida (409),
pagamento aprovado/recusado, replay idempotente, resgate sem saldo, portabilidade,
anonimização e auditoria de ação sensível.

## Segurança e LGPD

### Dados pessoais tratados

| Dado | Finalidade | Base legal | Onde fica |
|---|---|---|---|
| nome, e-mail, telefone | identificação, contato e entrega | execução de contrato (art. 7º, V) | `usuarios` |
| senha | autenticação | execução de contrato | `usuarios.senha_hash` (**bcrypt**, nunca texto puro) |
| histórico de pedidos | obrigação fiscal e suporte | obrigação legal (art. 7º, II) | `pedidos`, `pedido_itens` |
| pontos de fidelidade | programa de vantagens | **consentimento** (art. 7º, I) | `pontos_transacoes` |
| IP e requestId | segurança e rastreabilidade | legítimo interesse (art. 7º, IX) | `auditoria_logs` |

### Controles implementados

- **Senha:** bcrypt (passlib), nunca retorna em resposta nem em log.
- **Autenticação:** JWT HS256 (60 min) + refresh token rotativo armazenado apenas como SHA-256.
- **Autorização:** `require_perfis` aplicado por endpoint; matriz de transições por perfil.
- **Minimização:** `UsuarioResumo` não expõe e-mail/telefone; e-mail de falha de login é mascarado
  (`cl***@raizes.com.br`); política de `details` não devolve stack trace.
- **Auditoria append-only:** `auditoria_logs` registra login, leitura de dados pessoais,
  exportação, anonimização, pedidos, pagamentos e estoque, com `requestId` e IP.
- **Consentimento:** obrigatório no cadastro (`consentimentoLgpd`), com carimbo de data/hora;
  resgate de fidelidade exige consentimento vigente.

### Retenção e eliminação

| Dado | Retenção | Ação |
|---|---|---|
| Conta e dados cadastrais | enquanto ativa ou até o titular solicitar exclusão | `DELETE /usuarios/me` → anonimização |
| Pedidos e pagamentos | 5 anos (fiscal/contábil) | mantidos, desvinculados de PII após anonimização |
| Logs de auditoria | 12 meses | append-only; sem dados sensíveis no payload |
| Refresh tokens | expiram em 7 dias | revogados no logout e na anonimização |

`DELETE /usuarios/me` substitui nome por "Titular anonimizado", e-mail por endereço sintético em
domínio reservado (`.invalid`), limpa telefone, invalida a senha com hash aleatório descartado,
revoga tokens, marca a conta como inativa e preserva os pedidos (obrigação legal).

## Referências

BRASIL. **Lei nº 13.709, de 14 de agosto de 2018** — Lei Geral de Proteção de Dados Pessoais
(LGPD). Brasília, DF: Presidência da República, 2018.

ASSOCIAÇÃO BRASILEIRA DE NORMAS TÉCNICAS. **NBR 14724**: informação e documentação — trabalhos
acadêmicos — apresentação. Rio de Janeiro: ABNT, 2011.

ASSOCIAÇÃO BRASILEIRA DE NORMAS TÉCNICAS. **NBR 6023**: informação e documentação — referências
— elaboração. Rio de Janeiro: ABNT, 2018.

FASTAPI. **FastAPI documentation**. Disponível em: https://fastapi.tiangolo.com. Acesso em: 2026.

SQLALCHEMY. **SQLAlchemy 2.0 documentation**. Disponível em:
https://docs.sqlalchemy.org/en/20/. Acesso em: 2026.

ALEMBIC. **Alembic documentation**. Disponível em: https://alembic.sqlalchemy.org. Acesso em: 2026.

PYDANTIC. **Pydantic v2 documentation**. Disponível em: https://docs.pydantic.dev. Acesso em: 2026.

OWASP FOUNDATION. **OWASP Top 10 — 2021**. Disponível em:
https://owasp.org/Top10/. Acesso em: 2026.

OWASP FOUNDATION. **API Security Top 10 — 2023**. Disponível em:
https://owasp.org/API-Security/. Acesso em: 2026.

## Autor

**Agatha Santana Souza** — RU: 4992316

---

Projeto acadêmico desenvolvido para a disciplina de Projeto Multidisciplinar (Eletiva IV).
