# Módulo: Gerenciamento de Projetos e Usuários

Microsserviço da **Plataforma de Documentação Inteligente de Projetos de
Engenharia de Software** (UPM — Engenharia de Software). Este módulo é a porta
de entrada do sistema: autentica usuários, controla papéis (RBAC), gerencia
equipes e projetos e oferece recomendações por IA com base no histórico de
atividades.

> **Status:** funcional, com API estável e frontend integrado.

---

## Sumário
1. [Visão geral](#visão-geral)
2. [Stack](#stack)
3. [Como rodar](#como-rodar)
4. [Variáveis de ambiente](#variáveis-de-ambiente)
5. [Estrutura do projeto](#estrutura-do-projeto)
6. [API — referência completa](#api--referência-completa)
7. [Integração com outros módulos](#integração-com-outros-módulos)
8. [Funcionalidade de IA](#funcionalidade-de-ia)
9. [Robustez](#robustez)

---

## Visão geral

| Responsabilidade | Descrição |
|---|---|
| Autenticação | Cadastro e login via JWT (Bearer token), com hash de senha (bcrypt) |
| Autorização (RBAC) | Três papéis: **admin** (Tech Lead/Arquiteto), **manager** (PM), **contributor** (Desenvolvedor) |
| Equipes | CRUD, membros, ownership |
| Projetos | CRUD, associação a equipes, membros com papel próprio (admin/editor/viewer/contributor) |
| IA | Recomendação de projetos com base no histórico de atividade do usuário (TF-IDF + cosine similarity) |
| Integração | Endpoints públicos para outros módulos validarem sessão, consultarem usuários e checarem permissões |

---

## Stack

- **Backend:** Python 3.10+ · FastAPI · SQLAlchemy 2 (async) · Pydantic v2
- **Auth:** PyJWT · passlib + bcrypt
- **Banco:** SQLite (default — zero setup) · PostgreSQL suportado
- **IA:** scikit-learn (TF-IDF + cosine similarity)
- **Frontend:** HTML + CSS + JavaScript ES modules (sem build, sem framework) — servido pelo próprio FastAPI

---

## Como rodar

### 1. Clone e instale
```bash
git clone <repo>
cd Gerenciamento_de_projetos-users
python -m venv .venv
# Linux / Mac:
source .venv/bin/activate
# Windows (PowerShell):
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### 2. (Opcional) Configure o `.env`
```bash
cp .env.example .env     # Linux/Mac
copy .env.example .env   # Windows
```
Sem `.env` os defaults rodam (SQLite + secret de dev). **Em produção, gere um `SECRET_KEY` forte.**

### 3. Popule o banco com dados de exemplo
```bash
python -m app.scripts.seed_database
```
Cria 5 usuários, 3 equipes, 5 projetos e ~50 atividades. Todos com senha **`password123`**.

### 4. Suba o servidor
```bash
uvicorn app.main:app --reload
```

Acesse:
- **Interface web:** http://localhost:8000/
- **Documentação interativa (Swagger):** http://localhost:8000/docs
- **Documentação alternativa (ReDoc):** http://localhost:8000/redoc

### Credenciais de teste
| Usuário | Email | Papel | Senha |
|---|---|---|---|
| `admin_user` | admin@example.com | admin | `password123` |
| `manager_alice` | alice@example.com | manager | `password123` |
| `manager_diana` | diana@example.com | manager | `password123` |
| `contributor_bob` | bob@example.com | contributor | `password123` |
| `contributor_charlie` | charlie@example.com | contributor | `password123` |

---

## Variáveis de ambiente

| Variável | Default | Descrição |
|---|---|---|
| `APP_NAME` | `Project Management Microservice` | Nome do serviço |
| `APP_VERSION` | `1.0.0` | Versão |
| `DEBUG` | `True` | Modo debug (auto-reload, logs verbosos) |
| `DATABASE_URL` | `sqlite+aiosqlite:///./project_management.db` | URL do banco. Para Postgres: `postgresql+asyncpg://user:pw@host:5432/db` |
| `SQLALCHEMY_ECHO` | `False` | Loga todas as queries (útil para debug) |
| `SECRET_KEY` | `change-me-...` | **Mude em produção!** Use `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `ALGORITHM` | `HS256` | Algoritmo do JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` (24h) | Validade do token |
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8000` | Porta |
| `CORS_ORIGINS` | `*` | Origens permitidas (CSV). Restrinja em produção |
| `INGESTION_SERVICE_URL` | _(vazio)_ | URL do módulo de Ingestão (Grupo 2) |
| `REPORTS_SERVICE_URL` | _(vazio)_ | URL do módulo de Relatórios (Grupo 3) |
| `PRESENTATIONS_SERVICE_URL` | _(vazio)_ | URL do módulo de Apresentações (Grupo 4) |
| `DIAGRAMS_SERVICE_URL` | _(vazio)_ | URL do módulo de Diagramas (Grupo 5) |
| `CHAT_SERVICE_URL` | _(vazio)_ | URL do módulo de Chat IA (Grupo 6) |

---

## Estrutura do projeto

```
.
├── app/                            # Backend (FastAPI)
│   ├── main.py                     # entrypoint, CORS, error handlers, static
│   ├── config.py                   # settings (lê .env)
│   ├── database.py                 # engine async + session factory
│   ├── models/__init__.py          # tabelas SQLAlchemy
│   ├── schemas/__init__.py         # Pydantic v2 (request/response)
│   ├── routes/
│   │   ├── auth.py                 # login, register, validate, me
│   │   ├── users.py                # CRUD de usuários
│   │   ├── teams.py                # CRUD de equipes + membros
│   │   ├── projects.py             # CRUD de projetos + membros
│   │   ├── recommendations.py      # IA + tracking de atividade
│   │   └── integration.py          # endpoints para os outros módulos
│   ├── services/
│   │   ├── rbac.py                 # checagens de permissão dependentes de recurso
│   │   └── recommendations.py      # motor TF-IDF
│   ├── utils/
│   │   ├── dependencies.py         # get_current_user, require_admin, etc.
│   │   └── security.py             # hash_password, JWT
│   └── scripts/seed_database.py    # popular dados de exemplo
├── frontend/                       # SPA HTML+JS vanilla
│   ├── index.html
│   └── assets/
│       ├── styles.css
│       ├── api.js                  # wrapper fetch + auth
│       └── app.js                  # SPA (roteamento, views)
├── requirements.txt
├── .env.example
└── README.md
```

---

## API — referência completa

> Convenções:
> - Todos os endpoints (exceto `/health`, `/api/auth/register`, `/api/auth/login` e `/api/integration/config`) exigem `Authorization: Bearer <token>`.
> - Códigos HTTP: `200/201/204` sucesso · `400` payload inválido · `401` não autenticado · `403` sem permissão · `404` não encontrado · `409` conflito (duplicidade) · `422` validação · `503` banco indisponível.

### 🔐 Autenticação — `/api/auth`

| Método | Rota | Descrição | Auth |
|---|---|---|---|
| `POST` | `/api/auth/register` | Auto-registro público. Sempre cria como `contributor`. Retorna token. | público |
| `POST` | `/api/auth/login` | Login JSON (`username_or_email` + `password`). Retorna token. | público |
| `GET` | `/api/auth/me` | Dados do usuário autenticado. | bearer |
| `GET` | `/api/auth/validate` | **Para outros módulos:** valida um token. Sempre retorna 200 (`{valid: bool, ...}`). | bearer |

**Exemplo — login:**
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username_or_email":"admin_user","password":"password123"}'
```
Resposta:
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": { "id": 1, "username": "admin_user", "role": { "name": "admin" }, ... }
}
```

### 👥 Usuários — `/api/users`

| Método | Rota | Descrição | Auth / Papel |
|---|---|---|---|
| `POST` | `/api/users/` | Cria usuário com papel explícito. | admin |
| `GET` | `/api/users/` | Lista usuários (paginação `?skip=&limit=`). | autenticado |
| `GET` | `/api/users/{id}` | Detalhe (inclui papel). | autenticado |
| `PUT` | `/api/users/{id}` | Atualiza. Próprio usuário ou admin. Só admin pode mudar `role_id`/`is_active`. | autenticado |
| `DELETE` | `/api/users/{id}` | Soft-delete (desativa). | admin |
| `GET` | `/api/users/roles/list` | Lista papéis disponíveis. | autenticado |

### 🏢 Equipes — `/api/teams`

| Método | Rota | Descrição | Auth |
|---|---|---|---|
| `POST` | `/api/teams/` | Cria equipe (caller = owner). | manager/admin |
| `GET` | `/api/teams/?skip=&limit=&include_inactive=` | Lista equipes. | autenticado |
| `GET` | `/api/teams/{id}` | Detalhe com membros. | autenticado |
| `PUT` | `/api/teams/{id}` | Atualiza. Só owner ou admin. | autenticado |
| `DELETE` | `/api/teams/{id}` | Arquiva (soft-delete). Só owner ou admin. | autenticado |
| `POST` | `/api/teams/{team_id}/members/{user_id}` | Adiciona membro. Só owner ou admin. | autenticado |
| `DELETE` | `/api/teams/{team_id}/members/{user_id}` | Remove membro. Só owner ou admin. | autenticado |

### 📦 Projetos — `/api/projects`

| Método | Rota | Descrição | Auth |
|---|---|---|---|
| `POST` | `/api/projects/` | Cria projeto (caller = owner + project admin). Pode associar equipe (verifica acesso). | manager/admin |
| `GET` | `/api/projects/?skip=&limit=&include_inactive=&mine=` | Lista projetos. `mine=true` filtra os do usuário. | autenticado |
| `GET` | `/api/projects/{id}` | Detalhe com membros e papéis. | autenticado |
| `PUT` | `/api/projects/{id}` | Atualiza. Só owner ou project admin (ou admin global). | autenticado |
| `DELETE` | `/api/projects/{id}` | Arquiva. Só owner ou project admin. | autenticado |
| `POST` | `/api/projects/{pid}/members/{uid}?role=contributor` | Adiciona membro com papel (`admin`/`editor`/`viewer`/`contributor`). | project admin |
| `DELETE` | `/api/projects/{pid}/members/{uid}` | Remove membro. | project admin |

### ✨ Recomendações por IA — `/api/recommendations`

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/recommendations/me?top_k=5` | Recomendações para o próprio usuário. |
| `GET` | `/api/recommendations/users/{id}?top_k=5` | Recomendações para outro usuário. |
| `POST` | `/api/recommendations/activities` | Registra uma atividade (`view`/`edit`/`comment`/...) — alimenta a IA. |

### 🔌 Integração entre módulos — `/api/integration`

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/integration/config` | URLs públicas dos outros módulos (vem do `.env`). Usado pelo frontend para construir links. Público. |
| `GET` | `/api/integration/users/lookup?ids=1,2,3` | **Bulk lookup** de usuários por id (até 100). Para outros módulos enriquecerem listas. |
| `GET` | `/api/integration/projects/{pid}/access/{uid}` | Verifica se um usuário tem acesso a um projeto, retornando o papel. Para outros módulos checarem permissão antes de servir dados. |

### Saúde / utilidades

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/health` | Liveness probe. Público. |
| `GET` | `/` | Frontend (se `frontend/` existir) ou JSON com links para docs. |
| `GET` | `/docs`, `/redoc` | Documentação interativa (gerada pelo FastAPI). |

---

## Integração com outros módulos

Este módulo é a **fonte da verdade** para identidade, papéis e projetos.
Os outros 5 grupos da plataforma podem:

1. **Validar sessões.** Recebem um `Authorization: Bearer <token>` do frontend
   ou de outro serviço e fazem:
   ```http
   GET /api/auth/validate
   Authorization: Bearer <token>
   ```
   Retorna 200 com `{valid: true, user_id, role, ...}` ou `{valid: false}`.
   Nunca lança exceção HTTP, simplificando o tratamento.

2. **Buscar dados de usuário.** Para popular avatares/nomes em listas:
   ```http
   GET /api/integration/users/lookup?ids=1,2,3
   ```

3. **Verificar acesso a projeto.** Antes de servir relatórios, diagramas, etc:
   ```http
   GET /api/integration/projects/{pid}/access/{uid}
   ```

4. **Descobrir-se mutuamente.** Cada módulo publica sua URL via `*_SERVICE_URL`
   no `.env` deste serviço; o frontend e demais módulos as consultam em
   `GET /api/integration/config`. URLs ausentes viram `null` (placeholder
   desativado, não quebra o sistema).

**Contratos estáveis:** os schemas em `/api/integration/*` são separados dos
schemas internos (`UserMini`, `ProjectAccess`) — alterações neles são
intencionais, garantindo que os outros grupos não quebrem com refactors aqui.

---

## Funcionalidade de IA

Recomendação de projetos baseada em conteúdo:

1. **Coleta o perfil de atividade** do usuário nos últimos 90 dias (tags das
   ações `view`/`edit`/`comment`/...).
2. **Vetoriza** o perfil e cada projeto disponível com **TF-IDF** (uni e bigrams).
3. **Mede similaridade** via **cosine similarity**.
4. **Filtra e ordena** retornando os top-K mais relevantes (default 5),
   excluindo projetos onde o usuário já é membro.

**Fallback graceful:**
- Sem histórico de atividade → retorna projetos disponíveis com score 0 (para o
  usuário ainda ter sugestões iniciais).
- scikit-learn falha (instalação corrompida) → retorna projetos com score 0.
- O endpoint **nunca derruba o serviço**.

Atividades são gravadas automaticamente pelo frontend ao abrir um projeto, ou
manualmente via `POST /api/recommendations/activities`.

---

## Robustez

Princípios aplicados para que **uma falha local não derrube o sistema**:

- **Handlers globais de erro** convertem qualquer exceção em JSON estruturado:
  - `SQLAlchemyError` → `503 Database temporarily unavailable`
  - `RequestValidationError` → `422` com detalhes
  - `Exception` genérico → `500` com mensagem genérica (sem vazar stack trace)
- **Banco com `pool_pre_ping`** (Postgres): conexões mortas são recicladas.
- **JWT com expiração** e claims mínimos (`sub`, `exp`, `iss`).
- **Senhas hasheadas com bcrypt** — nunca em texto puro.
- **`/api/auth/validate` é tolerante a falhas:** retorna 200 com `valid:false`
  ao invés de lançar exceção, simplificando a vida dos outros módulos.
- **Frontend trata 401** automaticamente: limpa sessão e redireciona para
  login.
- **Timeouts** no cliente HTTP do frontend (15s default).
- **Recomendador com fallback** (ver seção IA).
- **CORS configurável** por env.

---

## Próximos passos sugeridos

- Adicionar testes automatizados (pytest + httpx) — útil para CI.
- Mover o seed para um endpoint admin (ou Alembic migrations) em produção.
- Substituir `SECRET_KEY` por leitura de secret manager em produção.
- (Opcional) Adicionar integração com LLM externo (Claude/OpenAI) para
  recomendações mais ricas — o serviço já está estruturado para isso
  (`source` no `RecommendationResponse`).
