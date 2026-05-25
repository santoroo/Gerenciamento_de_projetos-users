# Gerenciamento de Projetos e Usuarios

Microsservico da **Plataforma de Documentacao Inteligente de Projetos de Engenharia de Software** (UPM - Engenharia de Software).

Este modulo e a porta de entrada do sistema: autentica usuarios, controla papeis (RBAC), gerencia equipes e projetos e oferece recomendacoes por IA com base no historico de atividades.

**Autor:** Gabriel Santoro Silveira — [@santoroo](https://github.com/santoroo)

---

## Sumario

1. [Visao geral](#visao-geral)
2. [Arquitetura e Stack](#arquitetura-e-stack)
3. [Pre-requisitos](#pre-requisitos)
4. [Instalacao e execucao](#instalacao-e-execucao)
5. [Variaveis de ambiente](#variaveis-de-ambiente)
6. [Estrutura do projeto](#estrutura-do-projeto)
7. [API - referencia completa](#api--referencia-completa)
8. [Sistema de papeis (RBAC)](#sistema-de-papeis-rbac)
9. [Integracao com outros modulos](#integracao-com-outros-modulos)
10. [Funcionalidade de IA](#funcionalidade-de-ia)
11. [Frontend](#frontend)
12. [Robustez e tratamento de erros](#robustez-e-tratamento-de-erros)
13. [Decisoes tecnicas](#decisoes-tecnicas)

---

## Visao geral

| Responsabilidade | Descricao |
|---|---|
| Autenticacao | Cadastro e login via JWT (Bearer token), com hash de senha (bcrypt) |
| Autorizacao (RBAC) | Tres papeis: **admin** (Tech Lead/Arquiteto), **manager** (Gerente de Projetos), **contributor** (Desenvolvedor) |
| Equipes | CRUD completo, gerenciamento de membros, ownership |
| Projetos | CRUD completo, associacao a equipes, membros com papel proprio (admin/editor/viewer/contributor) |
| Recomendacao por IA | Sugestao de projetos com base no historico de atividade do usuario (TF-IDF + cosine similarity) |
| Integracao | Endpoints para outros modulos validarem sessao, consultarem usuarios e checarem permissoes |

---

## Arquitetura e Stack

### Backend
- **Python 3.10+** com **FastAPI** (framework async de alta performance)
- **SQLAlchemy 2** com suporte async (aiosqlite / asyncpg)
- **Pydantic v2** para validacao de dados (request/response schemas)
- **PyJWT** + **passlib/bcrypt** para autenticacao segura
- **scikit-learn** para o motor de recomendacao (TF-IDF + cosine similarity)

### Banco de dados
- **SQLite** por padrao (zero configuracao, ideal para desenvolvimento)
- **PostgreSQL** suportado via `asyncpg` (recomendado para producao)

### Frontend
- **HTML5 + CSS3 + JavaScript ES Modules** (sem build, sem framework)
- SPA com roteamento por hash, servida pelo proprio FastAPI
- Design responsivo com suporte a dark mode

### Diagrama de camadas
```
Frontend (SPA)  -->  FastAPI (Routes)  -->  Services (RBAC, IA)
                          |
                     SQLAlchemy ORM
                          |
                   SQLite / PostgreSQL
```

---

## Pre-requisitos

- **Python 3.10** ou superior
- **pip** (gerenciador de pacotes Python)
- **Git**

---

## Instalacao e execucao

### 1. Clone o repositorio
```bash
git clone https://github.com/santoroo/Gerenciamento_de_projetos-users.git
cd Gerenciamento_de_projetos-users
```

### 2. Crie e ative o ambiente virtual
```bash
python -m venv .venv

# Linux / Mac:
source .venv/bin/activate

# Windows (PowerShell):
.venv\Scripts\Activate.ps1

# Windows (CMD):
.venv\Scripts\activate.bat
```

### 3. Instale as dependencias
```bash
pip install -r requirements.txt
```

### 4. (Opcional) Configure o `.env`
```bash
# Linux/Mac:
cp .env.example .env

# Windows:
copy .env.example .env
```
Sem `.env` o sistema roda com os defaults (SQLite + secret de desenvolvimento).
**Em producao, gere um `SECRET_KEY` forte:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### 5. Inicie o servidor
```bash
uvicorn app.main:app --reload
```

Na primeira execucao, o sistema automaticamente:
- Cria as tabelas no banco de dados
- Cria os tres papeis (admin, manager, contributor)
- Cria o usuario administrador padrao

### 6. (Opcional) Popule com dados de exemplo
```bash
python -m app.scripts.seed_database
```
Cria 5 usuarios, 3 equipes, 5 projetos e atividades de exemplo.

### 7. Acesse a aplicacao

| Recurso | URL |
|---|---|
| Interface web | http://localhost:8000/ |
| Documentacao Swagger | http://localhost:8000/docs |
| Documentacao ReDoc | http://localhost:8000/redoc |
| Health check | http://localhost:8000/health |

### Credenciais padrao

O usuario administrador e criado automaticamente na primeira execucao:

| Usuario | Email | Papel | Senha |
|---|---|---|---|
| `admin_user` | admin@example.com | admin (Tech Lead) | `password123` |

Apos rodar o seed (opcional), tambem ficam disponiveis:

| Usuario | Email | Papel | Senha |
|---|---|---|---|
| `manager_alice` | alice@example.com | manager (Gerente) | `password123` |
| `manager_diana` | diana@example.com | manager (Gerente) | `password123` |
| `contributor_bob` | bob@example.com | contributor (Dev) | `password123` |
| `contributor_charlie` | charlie@example.com | contributor (Dev) | `password123` |

---

## Variaveis de ambiente

| Variavel | Default | Descricao |
|---|---|---|
| `APP_NAME` | `Project Management Microservice` | Nome do servico |
| `APP_VERSION` | `1.0.0` | Versao |
| `DEBUG` | `True` | Modo debug (auto-reload, logs verbosos) |
| `DATABASE_URL` | `sqlite+aiosqlite:///./project_management.db` | URL do banco. Para Postgres: `postgresql+asyncpg://user:pw@host:5432/db` |
| `SQLALCHEMY_ECHO` | `False` | Loga todas as queries SQL |
| `SECRET_KEY` | `change-me-...` | Chave para assinatura JWT. **Mude em producao!** |
| `ALGORITHM` | `HS256` | Algoritmo do JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` (24h) | Validade do token |
| `HOST` | `0.0.0.0` | Endereco de bind |
| `PORT` | `8000` | Porta |
| `CORS_ORIGINS` | `*` | Origens permitidas (CSV). Restrinja em producao |
| `INGESTION_SERVICE_URL` | _(vazio)_ | URL do modulo de Ingestao |
| `REPORTS_SERVICE_URL` | _(vazio)_ | URL do modulo de Relatorios |
| `PRESENTATIONS_SERVICE_URL` | _(vazio)_ | URL do modulo de Apresentacoes |
| `DIAGRAMS_SERVICE_URL` | _(vazio)_ | URL do modulo de Diagramas |
| `CHAT_SERVICE_URL` | _(vazio)_ | URL do modulo de Chat IA |

---

## Estrutura do projeto

```
.
├── app/                            # Backend (FastAPI)
│   ├── main.py                     # Entrypoint, CORS, error handlers, static files
│   ├── config.py                   # Settings (le .env via pydantic-settings)
│   ├── database.py                 # Engine async, session factory, bootstrap
│   ├── models/__init__.py          # Modelos SQLAlchemy (User, Team, Project, etc.)
│   ├── schemas/__init__.py         # Schemas Pydantic v2 (request/response)
│   ├── routes/
│   │   ├── auth.py                 # Login, registro, validacao de token
│   │   ├── users.py                # CRUD de usuarios (admin)
│   │   ├── teams.py                # CRUD de equipes + membros
│   │   ├── projects.py             # CRUD de projetos + membros
│   │   ├── recommendations.py      # Recomendacoes IA + tracking de atividade
│   │   └── integration.py          # Endpoints para outros microsservicos
│   ├── services/
│   │   ├── rbac.py                 # Checagens de permissao por recurso
│   │   └── recommendations.py      # Motor de recomendacao TF-IDF
│   ├── utils/
│   │   ├── dependencies.py         # get_current_user, require_admin, guards
│   │   └── security.py             # Hash de senha, JWT encode/decode
│   └── scripts/
│       └── seed_database.py        # Script para popular dados de exemplo
├── frontend/                       # SPA HTML+JS vanilla
│   ├── index.html                  # Pagina principal
│   └── assets/
│       ├── styles.css              # Estilos (responsivo + dark mode)
│       ├── api.js                  # Cliente HTTP com auth automatica
│       └── app.js                  # Aplicacao SPA (roteamento, views)
├── requirements.txt                # Dependencias Python
├── .env.example                    # Template de configuracao
├── .gitignore
└── README.md
```

---

## API - referencia completa

> **Convencoes:**
> - Todos os endpoints (exceto `/health`, `/api/auth/register`, `/api/auth/login` e `/api/integration/config`) exigem `Authorization: Bearer <token>`.
> - Codigos HTTP: `200/201/204` sucesso | `400` payload invalido | `401` nao autenticado | `403` sem permissao | `404` nao encontrado | `409` conflito (duplicidade) | `422` erro de validacao | `503` banco indisponivel.

### Autenticacao - `/api/auth`

| Metodo | Rota | Descricao | Auth |
|---|---|---|---|
| `POST` | `/api/auth/register` | Auto-registro publico. Cria como `contributor`. Retorna token. | publico |
| `POST` | `/api/auth/login` | Login JSON (`username_or_email` + `password`). Retorna token. | publico |
| `GET` | `/api/auth/me` | Dados do usuario autenticado. | bearer |
| `GET` | `/api/auth/validate` | Valida um token (para outros modulos). Retorna 200 sempre. | bearer |

**Exemplo - login:**
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username_or_email":"admin_user","password":"password123"}'
```
**Resposta:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": 1,
    "username": "admin_user",
    "role": { "name": "admin" }
  }
}
```

### Usuarios - `/api/users`

| Metodo | Rota | Descricao | Permissao |
|---|---|---|---|
| `POST` | `/api/users/` | Cria usuario com papel explicito | admin |
| `GET` | `/api/users/` | Lista usuarios (`?skip=&limit=`) | autenticado |
| `GET` | `/api/users/{id}` | Detalhe do usuario (inclui papel) | autenticado |
| `PUT` | `/api/users/{id}` | Atualiza. Proprio usuario ou admin. So admin muda `role_id`/`is_active` | autenticado |
| `DELETE` | `/api/users/{id}` | Desativa usuario (soft-delete) | admin |
| `GET` | `/api/users/roles/list` | Lista papeis disponiveis | publico |

### Equipes - `/api/teams`

| Metodo | Rota | Descricao | Permissao |
|---|---|---|---|
| `POST` | `/api/teams/` | Cria equipe (caller = owner) | manager/admin |
| `GET` | `/api/teams/` | Lista equipes (`?skip=&limit=&include_inactive=`) | autenticado |
| `GET` | `/api/teams/{id}` | Detalhe com membros | autenticado |
| `PUT` | `/api/teams/{id}` | Atualiza equipe | owner/admin |
| `DELETE` | `/api/teams/{id}` | Arquiva equipe (soft-delete) | owner/admin |
| `POST` | `/api/teams/{id}/members/{user_id}` | Adiciona membro | owner/admin |
| `DELETE` | `/api/teams/{id}/members/{user_id}` | Remove membro | owner/admin |

### Projetos - `/api/projects`

| Metodo | Rota | Descricao | Permissao |
|---|---|---|---|
| `POST` | `/api/projects/` | Cria projeto (caller = owner + project admin) | manager/admin |
| `GET` | `/api/projects/` | Lista projetos (`?skip=&limit=&include_inactive=&mine=`) | autenticado |
| `GET` | `/api/projects/{id}` | Detalhe com membros e papeis | autenticado |
| `PUT` | `/api/projects/{id}` | Atualiza projeto | owner/project admin |
| `DELETE` | `/api/projects/{id}` | Arquiva projeto (soft-delete) | owner/project admin |
| `POST` | `/api/projects/{id}/members/{user_id}?role=contributor` | Adiciona membro com papel | project admin |
| `DELETE` | `/api/projects/{id}/members/{user_id}` | Remove membro | project admin |

### Recomendacoes por IA - `/api/recommendations`

| Metodo | Rota | Descricao |
|---|---|---|
| `GET` | `/api/recommendations/me?top_k=5` | Recomendacoes para o usuario logado |
| `GET` | `/api/recommendations/users/{id}?top_k=5` | Recomendacoes para outro usuario |
| `POST` | `/api/recommendations/activities` | Registra atividade (view/edit/comment) - alimenta a IA |

### Integracao - `/api/integration`

| Metodo | Rota | Descricao |
|---|---|---|
| `GET` | `/api/integration/config` | URLs dos outros modulos (publico) |
| `GET` | `/api/integration/users/lookup?ids=1,2,3` | Busca usuarios por ID (bulk, ate 100) |
| `GET` | `/api/integration/projects/{pid}/access/{uid}` | Verifica acesso de usuario a projeto |

### Saude

| Metodo | Rota | Descricao |
|---|---|---|
| `GET` | `/health` | Liveness probe (publico) |
| `GET` | `/docs` | Documentacao interativa Swagger |
| `GET` | `/redoc` | Documentacao alternativa ReDoc |

---

## Sistema de papeis (RBAC)

O sistema implementa controle de acesso baseado em papeis em dois niveis:

### Papeis globais (aplicacao)

| Papel | Nome no sistema | Permissoes |
|---|---|---|
| **Tech Lead / Arquiteto** | `admin` | Acesso total: CRUD de usuarios, equipes, projetos. Pode alterar papeis e desativar contas. |
| **Gerente de Projetos** | `manager` | Cria e gerencia equipes e projetos. Nao gerencia usuarios. |
| **Desenvolvedor** | `contributor` | Visualiza equipes e projetos. Participa quando adicionado. Edita proprio perfil. |

### Papeis por projeto

Dentro de cada projeto, membros podem ter papeis especificos:

| Papel | Permissoes no projeto |
|---|---|
| `admin` | Edita projeto, adiciona/remove membros |
| `editor` | Edita conteudo do projeto |
| `viewer` | Apenas visualiza |
| `contributor` | Contribui com atividades |

### Fluxo de permissoes

```
Registro publico → contributor (padrao)
Admin cria usuario → qualquer papel
Admin promove usuario → PUT /api/users/{id} com role_id
```

O admin padrao (`admin_user`) e criado automaticamente na primeira execucao do servidor. Use-o para promover outros usuarios ou criar contas com papeis especificos.

---

## Integracao com outros modulos

Este modulo e a **fonte da verdade** para identidade, papeis e projetos na plataforma. Os demais modulos podem:

### 1. Validar sessoes
```http
GET /api/auth/validate
Authorization: Bearer <token>
```
Retorna `{"valid": true, "user_id": 1, "role": "admin", ...}` ou `{"valid": false}`.
Sempre retorna HTTP 200 (sem excecoes), simplificando o tratamento.

### 2. Buscar dados de usuario
```http
GET /api/integration/users/lookup?ids=1,2,3
```
Retorna nome, email e papel de ate 100 usuarios de uma vez.

### 3. Verificar acesso a projeto
```http
GET /api/integration/projects/{pid}/access/{uid}
```
Retorna se o usuario tem acesso e qual seu papel no projeto.

### 4. Descoberta de servicos
Cada modulo publica sua URL via variavel de ambiente (`*_SERVICE_URL`).
O frontend e demais modulos consultam `GET /api/integration/config`.
URLs ausentes aparecem como `null` (placeholder desativado, nao quebra o sistema).

---

## Funcionalidade de IA

### Motor de recomendacao

O sistema recomenda projetos relevantes para cada usuario com base em seu historico de atividades:

1. **Coleta de perfil:** analisa as atividades dos ultimos 90 dias (views, edits, comments) e extrai as tags associadas
2. **Vetorizacao:** transforma o perfil do usuario e cada projeto em vetores usando **TF-IDF** (uni e bigrams)
3. **Similaridade:** calcula **cosine similarity** entre o perfil e cada projeto candidato
4. **Ranking:** retorna os top-K projetos mais relevantes (padrao: 5), excluindo projetos onde o usuario ja e membro

### Fallback graceful

- Sem historico de atividade: retorna projetos disponiveis com score 0 (sugestoes iniciais)
- Falha no scikit-learn: retorna projetos com score 0 (nunca derruba o servico)
- Endpoint sempre retorna resposta valida

### Alimentando o recomendador

Atividades sao registradas automaticamente pelo frontend ao abrir um projeto, ou manualmente:
```bash
curl -X POST http://localhost:8000/api/recommendations/activities \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"project_id": 1, "activity_type": "view", "tags": "backend,api"}'
```

---

## Frontend

A interface web e uma SPA (Single Page Application) construida com HTML, CSS e JavaScript puro (sem framework, sem etapa de build).

### Paginas

| Rota | Descricao | Acesso |
|---|---|---|
| `#/login` | Tela de login | publico |
| `#/register` | Tela de registro | publico |
| `#/dashboard` | Painel principal com KPIs e recomendacoes | autenticado |
| `#/projects` | Lista de projetos + criacao | autenticado |
| `#/projects/:id` | Detalhe do projeto + membros | autenticado |
| `#/teams` | Lista de equipes + criacao | autenticado |
| `#/teams/:id` | Detalhe da equipe + membros | autenticado |
| `#/recommendations` | Recomendacoes de IA | autenticado |
| `#/users` | Gerenciamento de usuarios | admin |
| `#/profile` | Perfil do usuario logado | autenticado |

### Funcionalidades do frontend

- Autenticacao persistente via `localStorage` (token JWT)
- Logout automatico ao receber HTTP 401 (token expirado)
- Timeout de requisicoes (15s)
- Design responsivo (mobile-friendly)
- Suporte a dark mode (via `prefers-color-scheme`)
- Toasts para feedback visual
- Modais para criacao/edicao de recursos
- Sidebar com navegacao e links para modulos integrados

---

## Robustez e tratamento de erros

### Backend

- **Handlers globais de erro** convertem qualquer excecao em JSON estruturado:
  - `SQLAlchemyError` -> `503 Database temporarily unavailable`
  - `RequestValidationError` -> `422` com detalhes
  - `Exception` generico -> `500` sem vazar stack trace
- **Banco com `pool_pre_ping`** (Postgres): conexoes mortas sao recicladas automaticamente
- **JWT com expiracao** e claims minimos (`sub`, `exp`, `iss`)
- **Senhas hasheadas com bcrypt** (nunca armazenadas em texto puro)
- **`/api/auth/validate` tolerante a falhas:** retorna 200 com `valid:false` ao inves de excecao HTTP
- **Bootstrap automatico:** roles e admin criados na inicializacao (sem dependencia de seed manual)
- **CORS configuravel** por variavel de ambiente

### Frontend

- Tratamento de 401 (limpa sessao e redireciona para login)
- Timeouts em todas as requisicoes (15s)
- Feedback visual para erros de rede e API
- Validacao de formularios via HTML5

---

## Decisoes tecnicas

| Decisao | Justificativa |
|---|---|
| **FastAPI** | Framework async com auto-documentacao (Swagger/ReDoc), validacao automatica via Pydantic, alta performance |
| **SQLAlchemy async** | ORM maduro com suporte a operacoes assincronas, portabilidade entre SQLite e PostgreSQL |
| **SQLite como default** | Zero configuracao para desenvolvimento. Troca para Postgres alterando uma variavel |
| **JWT stateless** | Tokens auto-contidos permitem validacao sem consultar banco a cada request. Outros modulos validam localmente |
| **bcrypt** | Algoritmo de hash de senha resistente a ataques de forca bruta (work factor adaptavel) |
| **TF-IDF para recomendacao** | Algoritmo leve que roda sem GPU ou servico externo, adequado para o escopo do projeto |
| **Frontend sem framework** | Reduz complexidade e dependencias. Servido pelo proprio backend, sem CORS em desenvolvimento |
| **Soft-delete** | Usuarios e recursos sao desativados (nunca deletados), preservando integridade referencial |
| **Bootstrap automatico** | Admin e roles criados na inicializacao, eliminando dependencia de scripts manuais |
| **Schemas de integracao separados** | `UserMini` e `ProjectAccess` sao independentes dos schemas internos, evitando quebras nos modulos parceiros |

---

## Licenca

Projeto academico desenvolvido para a disciplina de Engenharia de Software na Universidade Presbiteriana Mackenzie (UPM).
