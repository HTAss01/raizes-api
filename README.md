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
- Cardápio e estoque por unidade
- Criação de pedido com registro obrigatório do canal de origem (`canalPedido`)
- Fluxo crítico: **Pedido → Pagamento (mock) → Atualização de status**
- Programa de fidelização com consentimento (LGPD)
- Logs de auditoria de ações sensíveis
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
├── infrastructure/          # Detalhes técnicos substituíveis
│   ├── db/
│   │   ├── base.py          # Base declarativa + convenção de constraints
│   │   ├── session.py       # Engine, sessão e dependência get_db
│   │   ├── models.py        # 14 modelos ORM (DER)
│   │   └── seed.py          # Dados iniciais idempotentes
│   └── security/password.py # Hash bcrypt
└── api/                     # Routers, schemas Pydantic e dependências
```

Dependência aponta sempre para dentro: `api → application → domain`,
`infrastructure` implementa o que o domínio/aplicação precisam.

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

_Em construção._

## Testes

_Em construção._

## Segurança e LGPD

_Em construção._

## Referências

_Em construção._

## Autor

**Agatha Santana Souza** — RU: 4992316

---

Projeto acadêmico desenvolvido para a disciplina de Projeto Multidisciplinar (Eletiva IV).
