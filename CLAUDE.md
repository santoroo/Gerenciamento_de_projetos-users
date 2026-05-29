# CLAUDE.md

Guia de contexto para o Claude Code trabalhar neste repositório. Mantenha este arquivo atualizado sempre que mudarmos arquitetura, integrações ou convenções importantes.

---

## O que é este projeto

**Módulo 1 — Gerenciamento de Projetos e Usuários** da **Plataforma de Documentação Inteligente de Projetos de Engenharia de Software** (UPM — Engenharia de Software).

É o microsserviço **porta de entrada** da plataforma: autentica usuários (JWT), aplica RBAC, gerencia equipes/projetos e recomenda projetos por IA (TF-IDF). Outros módulos consomem `/api/auth/validate` e `/api/integration/*` para validar sessão e dados de usuário/projeto.

- **Autor:** Gabriel Santoro Silveira ([@santoroo](https://github.com/santoroo))
- **Deploy de produção:** https://gerenciamento-projetos-users-e9fffgewdxe6gkfe.centralus-01.azurewebsites.net/
- **Pipeline:** `.github/workflows/main_gerenciamento-projetos-users.yml` (Azure App Service)

---

## Stack

- **Backend:** Python 3.10+, FastAPI, SQLAlchemy 2 async, Pydantic v2, PyJWT, passlib/bcrypt, scikit-learn (TF-IDF + cosine).
- **DB:** SQLite (default, `aiosqlite`) ou PostgreSQL (`asyncpg`).
- **Frontend:** HTML + CSS + JS vanilla (ES modules, sem build), servido pelo próprio FastAPI a partir de `frontend/`.
- **Deploy:** Azure App Service (gunicorn + uvicorn workers).

---

## Estrutura

```
app/
  main.py                  # FastAPI app, CORS, error handlers globais, static SPA
  config.py                # Settings (pydantic-settings, lê .env)
  database.py              # Engine async, get_db(), init_db() + bootstrap roles/admin
  models/__init__.py       # SQLAlchemy: Role, User, Team, TeamMember, Project, ProjectMember, UserActivity
  schemas/__init__.py      # Pydantic v2 (request/response)
  routes/
    auth.py                # /api/auth: register, login, login-form, me, validate
    users.py               # /api/users: CRUD (admin), roles/list (público)
    teams.py               # /api/teams: CRUD + membros
    projects.py            # /api/projects: CRUD + membros (com role por projeto)
    recommendations.py     # /api/recommendations: IA + log de atividade
    integration.py         # /api/integration: lookup de usuários, check de acesso
  services/
    rbac.py                # Checagens de permissão
    recommendations.py     # Motor TF-IDF
  utils/
    dependencies.py        # get_current_user, require_admin
    security.py            # hash/verify password, create/decode JWT
  scripts/
    seed_database.py       # Dados de exemplo (5 users, 3 teams, 5 projects)
frontend/
  index.html
  assets/
    api.js                 # Cliente HTTP com auth automática + timeout
    app.js                 # SPA: roteador por hash, navbar de plataforma, views
    styles.css
```

---

## RBAC (papéis)

**Globais (aplicação):**
| Papel | Role name | Quem é |
|---|---|---|
| Tech Lead/Arquiteto | `admin` | Acesso total |
| Gerente de Projetos | `manager` | CRUD de teams/projects |
| Desenvolvedor | `contributor` | Acesso restrito; padrão de auto-registro |

**Por projeto (em `project_members.role`):** `admin`, `editor`, `viewer`, `contributor`.

Bootstrap automático em `database.py:_bootstrap_defaults()`: cria as 3 roles + usuário `admin_user / password123` se não houver admin.

---

## Integração entre módulos da plataforma

Este módulo é a **fonte da verdade** para identidade/projetos. Os demais consomem:

- `GET /api/auth/validate` — valida bearer token (responde HTTP 200 sempre, com `valid: bool`).
- `GET /api/integration/users/lookup?ids=1,2,3` — bulk lookup (até 100 IDs).
- `GET /api/integration/projects/{pid}/access/{uid}` — checa acesso a projeto.
- `GET /api/integration/config` — descoberta de URLs dos outros módulos (público).

**SSO:** ao clicar num módulo na navbar (`frontend/assets/app.js` → `renderPlatformNavbar`), o token JWT é repassado via query string `?token=...`. Os módulos parceiros devem ler e validar via `/api/auth/validate`.

### Módulos da plataforma

| # | Módulo | Key no `integration_config` | URL atual |
|---|---|---|---|
| 1 | Gerenciamento de Projetos e Usuários | (este) | https://gerenciamento-projetos-users-e9fffgewdxe6gkfe.centralus-01.azurewebsites.net/ |
| 2 | Ingestão de Dados | `ingestion` | https://mod2eng.azurewebsites.net/ |
| 3 | Relatórios | `reports` | https://moduloderelatorios.azurewebsites.net/ |
| 4 | Apresentações | `presentations` | https://modulo4-apresentacoes-v2.azurewebsites.net/ |
| 5 | Diagramas | `diagrams` | https://modulo5-interface-e-nuvem.azurewebsites.net/ |
| 6 | Consulta | `chat` (placeholder) | _pendente_ |

> A chave `chat` no código guarda o slot do Módulo 6 (Consulta). Renomear quando a URL chegar.

---

## Como rodar local

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
# (opcional) python -m app.scripts.seed_database
```

Acesso: `http://localhost:8000/` (SPA), `/docs` (Swagger), `/health` (liveness).
Credenciais padrão: `admin_user / password123`.

---

## Convenções e armadilhas conhecidas

- **`expire_on_commit=False`** nas sessões: objetos continuam acessíveis pós-commit (necessário para o padrão `add → commit → return`).
- **`UserActivity.extra_data`**: o nome `metadata` é reservado pelo declarative_base do SQLAlchemy — não renomeie de volta.
- **Pool**: SQLite **não aceita** `pool_size`/`max_overflow`. O `_engine_kwargs()` já trata isso por driver.
- **`/api/auth/validate` sempre retorna 200**: para os módulos parceiros nunca precisarem capturar exceção HTTP.
- **CORS:** default é `*` (dev). Em produção, setar `CORS_ORIGINS` com a lista dos domínios dos módulos.
- **JWT:** `SECRET_KEY` precisa ser o **mesmo** entre todos os módulos que validam token localmente, ou todos chamam `/api/auth/validate`. Hoje os outros módulos chamam o endpoint (não dependem da chave).
- **Soft-delete:** users/teams/projects ficam com `is_active=False`, nunca são deletados.
- **Bootstrap:** ao subir o serviço com DB vazio, roles e admin são criados automaticamente — não depender de seed manual.

---

## Variáveis de ambiente relevantes

Ver `.env.example` para a lista completa. Críticas:

| Variável | Quando mexer |
|---|---|
| `SECRET_KEY` | Sempre em produção. Gerar com `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `DATABASE_URL` | Trocar para `postgresql+asyncpg://...` em produção |
| `CORS_ORIGINS` | Listar domínios dos outros módulos |
| `*_SERVICE_URL` | Quando um módulo parceiro mudar de URL ou for ao ar |

---

## Notas para o Claude

- **Mantenha este arquivo vivo:** ao mudar arquitetura, adicionar/remover módulo, alterar fluxo de auth ou integração entre serviços, **atualize aqui na mesma alteração**. A tabela de módulos é a parte mais propensa a ficar desatualizada.
- **Não rodar destrutivos** (`drop_db`, force-push, reset --hard) sem pedir confirmação.
- **Não commitar** sem o usuário pedir.
- **Frontend é vanilla JS sem build** — nenhuma transpilação, nenhum bundler. Mantenha módulos ES nativos.
