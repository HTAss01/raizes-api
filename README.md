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
├── domain/          # Entidades, regras de negócio e validações
├── application/     # Casos de uso e orquestração dos fluxos
├── infrastructure/  # Modelos SQLAlchemy, repositórios, pagamento mock, logs
└── api/             # Routers, schemas Pydantic, dependências de auth
```

_Detalhamento e diagramas em construção._

## Como executar

_Em construção._

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
