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
| DER (entidade-relacionamento) | `docs/diagramas/der.md` |
| Casos de uso + descrição do fluxo crítico | `docs/diagramas/casos-de-uso.md` |
| Diagrama de classes e máquina de estados | `docs/diagramas/classes.md` |
| Sequência Pedido → Pagamento → Status | `docs/diagramas/sequencia-pedido-pagamento.md` |
| Plano de testes (25 cenários) | `docs/PLANO_DE_TESTES.md` |
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

Para testar endpoints protegidos no Swagger: execute `POST /auth/login`, copie o `accessToken`,
clique em **Authorize** e cole o token (o esquema é `BearerAuth`).

### Endpoints por recurso

| Recurso | Endpoint | Autenticação / perfil |
|---|---|---|
| Autenticação | `POST /auth/login` | público |
| | `POST /auth/refresh`, `POST /auth/logout` | público (exige refresh token) |
| | `GET /auth/me` | JWT |
| Usuários | `POST /usuarios` | público (autocadastro — sempre perfil CLIENTE) |
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

- **Coleção:** `docs/postman/Raizes-API.postman_collection.json` (10 pastas, 59 requisições)
- **Environment:** `docs/postman/Raizes-API.postman_environment.json`
- **Plano com os 25 cenários:** `docs/PLANO_DE_TESTES.md`

Como executar:

1. Suba a API em `http://localhost:8000` com banco migrado e seed aplicado.
2. Importe coleção + environment no Postman.
3. **Collection Runner** → Run. As variáveis (`accessToken`, `pedidoId`, `pagamentoId`,
   `idempotencyKey`) são encadeadas pelos scripts de teste.
4. Rode em banco recém-semeado (a pasta de LGPD cadastra e depois anonimiza um cliente).

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
