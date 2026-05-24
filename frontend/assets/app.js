import { api, auth, ApiError } from "./api.js";

/* ============================================================
   tiny DOM helpers
   ============================================================ */
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") node.className = v;
    else if (k === "html") node.innerHTML = v;
    else if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2).toLowerCase(), v);
    else node.setAttribute(k, v === true ? "" : v);
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    node.appendChild(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

const fmtDate = (s) => {
  if (!s) return "—";
  try { return new Date(s).toLocaleDateString("pt-BR", { day: "2-digit", month: "short", year: "numeric" }); }
  catch { return s; }
};
const initials = (name) => (name || "?").trim().split(/\s+/).map(x => x[0]).slice(0, 2).join("").toUpperCase();
const ptRole = (name) => ({ admin: "Tech Lead", manager: "Gerente de Projetos", contributor: "Desenvolvedor" }[name] || name || "—");

function toast(message, type = "info", ms = 3500) {
  const t = el("div", { class: `toast ${type}` }, message);
  $("#toast-container").appendChild(t);
  setTimeout(() => t.remove(), ms);
}

function loading(text = "Carregando…") {
  return el("div", { class: "loading" }, el("span", { class: "spinner" }), text);
}

function emptyState(title, hint, action) {
  return el("div", { class: "empty" },
    el("h3", {}, title),
    el("p", {}, hint || ""),
    action,
  );
}

function errorBox(err) {
  const msg = err instanceof ApiError ? err.message : String(err?.message || err);
  return el("div", { class: "alert-error" }, msg);
}

/* ============================================================
   modal
   ============================================================ */
function openModal({ title, body, footer, onClose }) {
  const close = () => { backdrop.remove(); onClose?.(); };
  const modal = el("div", { class: "modal" },
    el("div", { class: "modal-header" },
      el("h2", {}, title),
      el("button", { class: "modal-close", "aria-label": "Fechar", onclick: close }, "×"),
    ),
    el("div", { class: "modal-body" }, body),
    footer ? el("div", { class: "modal-footer" }, footer) : null,
  );
  const backdrop = el("div", { class: "modal-backdrop", onclick: (e) => { if (e.target === backdrop) close(); } }, modal);
  document.body.appendChild(backdrop);
  return { close };
}

// Build a footer-submit button that triggers the given form even though it
// lives outside the <form> element (the form sits in modal-body, buttons in
// modal-footer). Uses requestSubmit so HTML5 validation still runs.
function submitFor(form, label = "Salvar") {
  return el("button", {
    class: "btn btn-primary",
    type: "button",
    onclick: () => form.requestSubmit ? form.requestSubmit() : form.dispatchEvent(new Event("submit", { cancelable: true })),
  }, label);
}

/* ============================================================
   integration config cache
   ============================================================ */
let _integrationCfg = null;
async function getIntegration() {
  if (_integrationCfg) return _integrationCfg;
  try { _integrationCfg = await api.integrationConfig(); }
  catch { _integrationCfg = { this_service: {}, modules: {} }; }
  return _integrationCfg;
}

/* ============================================================
   router
   ============================================================ */
const routes = {};
function route(path, handler, opts = {}) { routes[path] = { handler, opts }; }

function match(hash) {
  const clean = (hash || "#/dashboard").replace(/^#/, "");
  for (const [pattern, value] of Object.entries(routes)) {
    const keys = [];
    const re = new RegExp("^" + pattern.replace(/:([\w]+)/g, (_, k) => { keys.push(k); return "([^/]+)"; }) + "$");
    const m = clean.match(re);
    if (m) {
      const params = Object.fromEntries(keys.map((k, i) => [k, decodeURIComponent(m[i + 1])]));
      return { handler: value.handler, opts: value.opts, params };
    }
  }
  return null;
}

async function renderRoute() {
  const root = $("#app");
  const hash = window.location.hash || "#/dashboard";
  const matched = match(hash);

  const isAuth = !!auth.token;
  const isAuthPath = hash.startsWith("#/login") || hash.startsWith("#/register");

  if (!isAuth && !isAuthPath) {
    window.location.hash = "#/login";
    return;
  }
  if (isAuth && isAuthPath) {
    window.location.hash = "#/dashboard";
    return;
  }
  if (!matched) {
    root.innerHTML = "";
    root.appendChild(renderShell(emptyState("Página não encontrada", "Verifique o endereço.")));
    return;
  }

  if (matched.opts.adminOnly && !auth.isAdmin()) {
    root.innerHTML = "";
    root.appendChild(renderShell(emptyState("Acesso negado", "Esta área é restrita a administradores.")));
    return;
  }

  root.innerHTML = "";
  if (isAuthPath) {
    root.appendChild(await matched.handler(matched.params));
  } else {
    const content = el("div", {}, loading());
    root.appendChild(renderShell(content));
    try {
      const view = await matched.handler(matched.params);
      content.innerHTML = "";
      content.appendChild(view);
    } catch (err) {
      content.innerHTML = "";
      content.appendChild(errorBox(err));
    }
  }
  highlightNav();
}

window.addEventListener("hashchange", renderRoute);

/* ============================================================
   app shell (sidebar + main)
   ============================================================ */
function renderShell(content) {
  const u = auth.user;
  const sidebar = el("aside", { class: "sidebar" },
    el("div", { class: "brand" },
      el("div", { class: "logo" }, "P"),
      el("div", {},
        el("strong", {}, "Plataforma"),
        el("small", {}, "Gestão de Projetos"),
      ),
    ),
    el("nav", { class: "nav" },
      navLink("#/dashboard", "Dashboard", "🏠"),
      navLink("#/projects", "Projetos", "📦"),
      navLink("#/teams", "Equipes", "👥"),
      navLink("#/recommendations", "Recomendações", "✨"),
      auth.isAdmin() ? navLink("#/users", "Usuários", "🛡️") : null,
      navLink("#/profile", "Meu Perfil", "👤"),
    ),
    el("div", { class: "nav-section" }, "Outros módulos"),
    el("div", { class: "integrations", id: "integrations-list" }, loading()),
    el("div", { class: "sidebar-footer" },
      el("div", { class: "user" },
        el("div", { class: "avatar" }, initials(u?.full_name || u?.username)),
        el("div", {},
          el("div", {}, u?.full_name || u?.username || "—"),
          el("small", { class: "muted" }, ptRole(u?.role?.name)),
        ),
      ),
      el("button", { class: "btn btn-ghost btn-sm btn-block", onclick: logout }, "Sair"),
    ),
  );
  const main = el("main", {}, content);
  const shell = el("div", { class: "shell" }, sidebar, main);
  // populate integrations async
  getIntegration().then((cfg) => {
    const list = $("#integrations-list");
    if (!list) return;
    list.innerHTML = "";
    const labels = {
      ingestion: "Ingestão",
      reports: "Relatórios",
      presentations: "Apresentações",
      diagrams: "Diagramas",
      chat: "Chat IA",
    };
    for (const [key, label] of Object.entries(labels)) {
      const url = cfg.modules?.[key];
      const enabled = !!url;
      const link = el(enabled ? "a" : "div",
        { class: `integration-link ${enabled ? "enabled" : "disabled"}`, href: enabled ? url : null, target: enabled ? "_blank" : null, rel: "noopener" },
        el("span", {}, label),
        el("span", { class: "status" }, enabled ? "↗" : "—"),
      );
      list.appendChild(link);
    }
  });
  return shell;
}

function navLink(href, label, icon) {
  return el("a", { href, "data-nav": href },
    el("span", { class: "icon" }, icon),
    el("span", {}, label),
  );
}

function highlightNav() {
  const hash = window.location.hash || "#/dashboard";
  $$("[data-nav]").forEach(a => {
    const base = a.getAttribute("data-nav");
    a.classList.toggle("active", hash === base || hash.startsWith(base + "/"));
  });
}

async function logout() {
  auth.clear();
  _integrationCfg = null;
  window.location.hash = "#/login";
}

/* ============================================================
   page: LOGIN
   ============================================================ */
route("/login", async () => {
  const errBox = el("div");
  const form = el("form", {
    onsubmit: async (e) => {
      e.preventDefault();
      errBox.innerHTML = "";
      const fd = new FormData(form);
      const btn = $("button[type=submit]", form);
      btn.disabled = true;
      btn.textContent = "Entrando…";
      try {
        const res = await api.login(fd.get("username_or_email"), fd.get("password"));
        auth.set(res);
        toast("Bem-vindo, " + (res.user.full_name || res.user.username) + "!", "success");
        window.location.hash = "#/dashboard";
      } catch (err) {
        errBox.appendChild(errorBox(err));
      } finally {
        btn.disabled = false;
        btn.textContent = "Entrar";
      }
    }
  },
    errBox,
    field("username_or_email", "Usuário ou email", { required: true, autofocus: true }),
    field("password", "Senha", { type: "password", required: true, minlength: 8 }),
    el("button", { class: "btn btn-primary btn-block", type: "submit" }, "Entrar"),
    el("p", { class: "switch" }, "Não tem conta? ", el("a", { href: "#/register" }, "Criar conta")),
  );

  return el("div", { class: "auth-shell" },
    el("div", { class: "auth-card" },
      el("h1", {}, "Entrar"),
      el("p", { class: "subtitle" }, "Plataforma de Documentação Inteligente"),
      form,
    ),
  );
});

/* ============================================================
   page: REGISTER
   ============================================================ */
route("/register", async () => {
  const errBox = el("div");
  const form = el("form", {
    onsubmit: async (e) => {
      e.preventDefault();
      errBox.innerHTML = "";
      const fd = new FormData(form);
      const btn = $("button[type=submit]", form);
      btn.disabled = true; btn.textContent = "Criando…";
      try {
        const res = await api.register({
          username: fd.get("username"),
          email: fd.get("email"),
          full_name: fd.get("full_name") || null,
          password: fd.get("password"),
        });
        auth.set(res);
        toast("Conta criada com sucesso!", "success");
        window.location.hash = "#/dashboard";
      } catch (err) {
        errBox.appendChild(errorBox(err));
      } finally {
        btn.disabled = false; btn.textContent = "Criar conta";
      }
    },
  },
    errBox,
    field("full_name", "Nome completo"),
    field("username", "Nome de usuário", { required: true, minlength: 3 }),
    field("email", "Email", { type: "email", required: true }),
    field("password", "Senha", { type: "password", required: true, minlength: 8, hint: "Mínimo de 8 caracteres" }),
    el("button", { class: "btn btn-primary btn-block", type: "submit" }, "Criar conta"),
    el("p", { class: "switch" }, "Já tem conta? ", el("a", { href: "#/login" }, "Fazer login")),
  );
  return el("div", { class: "auth-shell" },
    el("div", { class: "auth-card" },
      el("h1", {}, "Criar conta"),
      el("p", { class: "subtitle" }, "Você começará como Desenvolvedor"),
      form,
    ),
  );
});

function field(name, label, opts = {}) {
  const hint = opts.hint;
  const inputAttrs = { name, id: `f-${name}`, ...opts };
  delete inputAttrs.hint;
  return el("div", { class: "field" },
    el("label", { for: `f-${name}` }, label),
    el("input", inputAttrs),
    hint ? el("span", { class: "hint" }, hint) : null,
  );
}

/* ============================================================
   page: DASHBOARD
   ============================================================ */
route("/dashboard", async () => {
  const [me, projects, teams, recs] = await Promise.all([
    api.me().catch(() => auth.user),
    api.listProjects({ limit: 100 }).catch(() => []),
    api.listTeams({ limit: 100 }).catch(() => []),
    api.myRecommendations(3).catch(() => ({ recommendations: [] })),
  ]);
  // refresh stored user
  if (me) auth.set({ user: me });

  const myProjects = projects.filter(p => p.members?.some(m => m.user_id === me.id));

  const kpis = el("div", { class: "kpi-grid" },
    kpi("Meus projetos", myProjects.length, "primary"),
    kpi("Projetos no sistema", projects.length, "success"),
    kpi("Equipes", teams.length, "warning"),
    kpi("Recomendações novas", recs.recommendations.length, "primary"),
  );

  const recCards = recs.recommendations.length
    ? el("div", { class: "grid" }, ...recs.recommendations.map(r => projectRecCard(r)))
    : emptyState("Sem recomendações ainda",
        "Interaja com projetos (visualize, comente, edite) para a IA aprender suas preferências.");

  const recentProjects = projects.slice(0, 6);

  return el("div", {},
    el("div", { class: "page-header" },
      el("div", { class: "title" },
        el("h1", {}, "Olá, " + (me?.full_name || me?.username) + "!"),
        el("span", { class: "subtitle" }, ptRole(me?.role?.name)),
      ),
    ),
    kpis,

    el("h2", {}, "✨ Recomendações de IA para você"),
    el("p", { class: "subtitle", style: "margin-bottom: 1rem; color: var(--text-muted);" },
      "Sugestões geradas a partir do seu histórico de atividades (TF-IDF)."),
    recCards,

    el("h2", { style: "margin-top: 2rem;" }, "Projetos recentes"),
    recentProjects.length
      ? el("div", { class: "grid" }, ...recentProjects.map(projectCard))
      : emptyState("Nenhum projeto",
          "Crie um projeto para começar.",
          auth.isManager() ? el("button", { class: "btn btn-primary", onclick: () => window.location.hash = "#/projects" }, "Ir para Projetos") : null),
  );
});

function kpi(label, value, cls) {
  return el("div", { class: `kpi ${cls}` },
    el("div", { class: "label" }, label),
    el("div", { class: "value" }, value),
  );
}

function projectCard(p) {
  return el("a", { class: "card", href: `#/projects/${p.id}`, style: "color: inherit; text-decoration: none;" },
    el("h3", {}, p.name),
    el("div", { class: "meta" }, "Criado em " + fmtDate(p.created_at)),
    el("p", {}, (p.description || "—").slice(0, 140)),
    el("div", { class: "tags" }, ...(p.tags ? p.tags.split(",").map(t => el("span", { class: "tag" }, t.trim())) : [])),
  );
}

function projectRecCard(r) {
  return el("a", { class: "card", href: `#/projects/${r.project_id}`, style: "color: inherit; text-decoration: none;" },
    el("h3", {}, r.project_name),
    el("div", { class: "meta" }, "Similaridade: " + (r.similarity_score * 100).toFixed(0) + "%"),
    el("p", {}, (r.description || "—").slice(0, 120)),
    el("div", { class: "tag" }, r.reason),
  );
}

/* ============================================================
   page: RECOMMENDATIONS
   ============================================================ */
route("/recommendations", async () => {
  const recs = await api.myRecommendations(10);
  return el("div", {},
    el("div", { class: "page-header" },
      el("div", { class: "title" }, el("h1", {}, "Recomendações de IA"),
        el("span", { class: "subtitle" }, "Fonte: " + recs.source)),
      el("button", { class: "btn", onclick: () => renderRoute() }, "Atualizar"),
    ),
    recs.recommendations.length
      ? el("div", { class: "grid" }, ...recs.recommendations.map(projectRecCard))
      : emptyState("Nada a recomendar",
          "Visualize, comente ou edite projetos para a IA aprender suas preferências."),
  );
});

/* ============================================================
   page: PROJECTS (list)
   ============================================================ */
route("/projects", async () => {
  const projects = await api.listProjects({ limit: 200, include_inactive: false });

  const header = el("div", { class: "page-header" },
    el("div", { class: "title" }, el("h1", {}, "Projetos")),
    auth.isManager()
      ? el("button", { class: "btn btn-primary", onclick: openCreateProjectModal }, "+ Novo projeto")
      : null,
  );

  if (!projects.length) {
    return el("div", {}, header, emptyState("Nenhum projeto", "Que tal criar o primeiro?"));
  }

  const rows = projects.map(p =>
    el("tr", { onclick: () => window.location.hash = `#/projects/${p.id}`, style: "cursor: pointer;" },
      el("td", {}, el("strong", {}, p.name)),
      el("td", {}, p.description?.slice(0, 80) || "—"),
      el("td", {}, el("div", { class: "tags" },
        ...(p.tags ? p.tags.split(",").slice(0, 3).map(t => el("span", { class: "tag" }, t.trim())) : ["—"]),
      )),
      el("td", {}, (p.members?.length || 0)),
      el("td", {}, p.is_active ? el("span", { class: "badge" }, "Ativo") : el("span", { class: "badge inactive" }, "Arquivado")),
      el("td", {}, fmtDate(p.created_at)),
    ),
  );

  return el("div", {},
    header,
    el("div", { class: "table-wrap" },
      el("table", {},
        el("thead", {}, el("tr", {},
          el("th", {}, "Nome"), el("th", {}, "Descrição"), el("th", {}, "Tags"),
          el("th", {}, "Membros"), el("th", {}, "Status"), el("th", {}, "Criado"))),
        el("tbody", {}, ...rows),
      ),
    ),
  );
});

async function openCreateProjectModal() {
  let teams = [];
  try { teams = await api.listTeams({ limit: 100 }); } catch {}
  const form = el("form", {});
  form.appendChild(field("name", "Nome do projeto", { required: true, minlength: 1 }));
  form.appendChild(el("div", { class: "field" },
    el("label", { for: "f-description" }, "Descrição"),
    el("textarea", { id: "f-description", name: "description", rows: 3 }),
  ));
  form.appendChild(field("tags", "Tags (separadas por vírgula)", { placeholder: "ex: backend, api, python" }));
  const select = el("select", { id: "f-team_id", name: "team_id" },
    el("option", { value: "" }, "— Sem equipe —"),
    ...teams.map(t => el("option", { value: t.id }, t.name)),
  );
  form.appendChild(el("div", { class: "field" },
    el("label", { for: "f-team_id" }, "Equipe"), select,
  ));
  const errBox = el("div");
  form.prepend(errBox);

  const submit = submitFor(form, "Criar");
  const cancel = el("button", { class: "btn", type: "button" }, "Cancelar");
  const { close } = openModal({
    title: "Novo projeto", body: form,
    footer: el("div", {}, cancel, submit),
  });
  cancel.onclick = close;

  form.onsubmit = async (e) => {
    e.preventDefault();
    errBox.innerHTML = "";
    submit.disabled = true;
    try {
      const fd = new FormData(form);
      const payload = {
        name: fd.get("name"),
        description: fd.get("description") || null,
        tags: fd.get("tags") || null,
        team_id: fd.get("team_id") ? Number(fd.get("team_id")) : null,
      };
      const created = await api.createProject(payload);
      toast("Projeto criado!", "success");
      close();
      window.location.hash = `#/projects/${created.id}`;
    } catch (err) {
      errBox.appendChild(errorBox(err));
      submit.disabled = false;
    }
  };
}

/* ============================================================
   page: PROJECT detail
   ============================================================ */
route("/projects/:id", async ({ id }) => {
  const project = await api.getProject(id);
  // Log a "view" activity (best-effort)
  api.logActivity({ project_id: project.id, activity_type: "view", tags: project.tags || null }).catch(() => {});

  const canEdit = auth.isAdmin() || project.owner_id === auth.user.id ||
    project.members?.some(m => m.user_id === auth.user.id && m.role === "admin");

  const header = el("div", { class: "page-header" },
    el("div", { class: "title" },
      el("h1", {}, project.name),
      project.is_active ? el("span", { class: "badge" }, "Ativo") : el("span", { class: "badge inactive" }, "Arquivado"),
    ),
    el("div", { class: "row" },
      canEdit ? el("button", { class: "btn", onclick: () => openEditProjectModal(project) }, "Editar") : null,
      canEdit && project.is_active ? el("button", { class: "btn btn-danger", onclick: () => archiveProject(project.id) }, "Arquivar") : null,
    ),
  );

  const info = el("div", { class: "card" },
    el("h3", {}, "Informações"),
    el("p", {}, project.description || "Sem descrição."),
    el("div", { class: "tags", style: "margin-top: .75rem;" },
      ...(project.tags ? project.tags.split(",").map(t => el("span", { class: "tag" }, t.trim())) : ["—"])),
    el("p", { class: "meta", style: "margin-top: 1rem;" },
      "Criado em " + fmtDate(project.created_at) + " • Atualizado em " + fmtDate(project.updated_at)),
  );

  const membersTable = el("div", { class: "table-wrap" },
    el("table", {},
      el("thead", {}, el("tr", {},
        el("th", {}, "Usuário"), el("th", {}, "Email"), el("th", {}, "Papel no projeto"),
        el("th", {}, "Entrou em"), el("th", {}, ""))),
      el("tbody", {}, ...(project.members || []).map(m =>
        el("tr", {},
          el("td", {}, m.username),
          el("td", {}, m.email),
          el("td", {}, el("span", { class: "badge" }, m.role)),
          el("td", {}, fmtDate(m.joined_at)),
          el("td", {},
            canEdit && m.user_id !== project.owner_id
              ? el("button", { class: "btn btn-sm btn-danger", onclick: () => removeProjectMember(project.id, m.user_id) }, "Remover")
              : "",
          ),
        ),
      )),
    ),
  );

  return el("div", {},
    header,
    el("div", { class: "grid", style: "grid-template-columns: 1fr; gap: 1rem;" },
      info,
      el("div", {},
        el("div", { class: "page-header" },
          el("div", { class: "title" }, el("h2", {}, "Membros (" + (project.members?.length || 0) + ")")),
          canEdit ? el("button", { class: "btn btn-primary btn-sm", onclick: () => openAddProjectMemberModal(project) }, "+ Adicionar membro") : null,
        ),
        membersTable,
      ),
    ),
  );
});

async function openEditProjectModal(project) {
  const form = el("form", {});
  form.appendChild(field("name", "Nome", { required: true, value: project.name }));
  form.appendChild(el("div", { class: "field" },
    el("label", { for: "f-description" }, "Descrição"),
    el("textarea", { id: "f-description", name: "description", rows: 3 }, project.description || ""),
  ));
  form.appendChild(field("tags", "Tags", { value: project.tags || "" }));
  const errBox = el("div");
  form.prepend(errBox);

  const submit = submitFor(form, "Salvar");
  const cancel = el("button", { class: "btn", type: "button" }, "Cancelar");
  const { close } = openModal({ title: "Editar projeto", body: form, footer: el("div", {}, cancel, submit) });
  cancel.onclick = close;
  form.onsubmit = async (e) => {
    e.preventDefault();
    errBox.innerHTML = "";
    submit.disabled = true;
    try {
      const fd = new FormData(form);
      await api.updateProject(project.id, {
        name: fd.get("name"),
        description: fd.get("description") || null,
        tags: fd.get("tags") || null,
      });
      toast("Projeto atualizado", "success");
      close();
      renderRoute();
    } catch (err) {
      errBox.appendChild(errorBox(err));
      submit.disabled = false;
    }
  };
}

async function archiveProject(id) {
  if (!confirm("Arquivar este projeto? Você poderá vê-lo depois marcando 'incluir arquivados'.")) return;
  try {
    await api.archiveProject(id);
    toast("Projeto arquivado", "success");
    window.location.hash = "#/projects";
  } catch (err) { toast(err.message, "error"); }
}

async function removeProjectMember(projectId, userId) {
  if (!confirm("Remover este membro do projeto?")) return;
  try {
    await api.removeProjectMember(projectId, userId);
    toast("Membro removido", "success");
    renderRoute();
  } catch (err) { toast(err.message, "error"); }
}

async function openAddProjectMemberModal(project) {
  let users = [];
  try { users = await api.listUsers({ limit: 200 }); } catch {}
  const memberIds = new Set((project.members || []).map(m => m.user_id));
  const candidates = users.filter(u => !memberIds.has(u.id) && u.is_active);

  const form = el("form", {});
  const select = el("select", { name: "user_id", required: true },
    el("option", { value: "" }, "— Selecione um usuário —"),
    ...candidates.map(u => el("option", { value: u.id }, `${u.full_name || u.username} (${u.email})`)),
  );
  const roleSelect = el("select", { name: "role" },
    el("option", { value: "contributor" }, "contributor"),
    el("option", { value: "editor" }, "editor"),
    el("option", { value: "viewer" }, "viewer"),
    el("option", { value: "admin" }, "admin"),
  );
  form.appendChild(el("div", { class: "field" }, el("label", {}, "Usuário"), select));
  form.appendChild(el("div", { class: "field" }, el("label", {}, "Papel no projeto"), roleSelect));
  const errBox = el("div"); form.prepend(errBox);

  const submit = submitFor(form, "Adicionar");
  const cancel = el("button", { class: "btn", type: "button" }, "Cancelar");
  const { close } = openModal({ title: "Adicionar membro", body: form, footer: el("div", {}, cancel, submit) });
  cancel.onclick = close;
  form.onsubmit = async (e) => {
    e.preventDefault();
    errBox.innerHTML = "";
    submit.disabled = true;
    try {
      const fd = new FormData(form);
      await api.addProjectMember(project.id, Number(fd.get("user_id")), fd.get("role"));
      toast("Membro adicionado", "success");
      close();
      renderRoute();
    } catch (err) {
      errBox.appendChild(errorBox(err));
      submit.disabled = false;
    }
  };
}

/* ============================================================
   page: TEAMS
   ============================================================ */
route("/teams", async () => {
  const teams = await api.listTeams({ limit: 200 });
  const header = el("div", { class: "page-header" },
    el("div", { class: "title" }, el("h1", {}, "Equipes")),
    auth.isManager()
      ? el("button", { class: "btn btn-primary", onclick: openCreateTeamModal }, "+ Nova equipe")
      : null,
  );
  if (!teams.length) return el("div", {}, header, emptyState("Nenhuma equipe", "Crie uma equipe para organizar pessoas."));

  return el("div", {}, header,
    el("div", { class: "grid" }, ...teams.map(t =>
      el("a", { class: "card", href: `#/teams/${t.id}`, style: "color: inherit; text-decoration: none;" },
        el("h3", {}, t.name),
        el("div", { class: "meta" }, (t.members?.length || 0) + " membros"),
        el("p", {}, t.description || "—"),
      ),
    )),
  );
});

async function openCreateTeamModal() {
  const form = el("form", {});
  form.appendChild(field("name", "Nome da equipe", { required: true }));
  form.appendChild(el("div", { class: "field" },
    el("label", { for: "f-description" }, "Descrição"),
    el("textarea", { id: "f-description", name: "description", rows: 3 }),
  ));
  const errBox = el("div"); form.prepend(errBox);
  const submit = submitFor(form, "Criar");
  const cancel = el("button", { class: "btn", type: "button" }, "Cancelar");
  const { close } = openModal({ title: "Nova equipe", body: form, footer: el("div", {}, cancel, submit) });
  cancel.onclick = close;
  form.onsubmit = async (e) => {
    e.preventDefault();
    errBox.innerHTML = "";
    submit.disabled = true;
    try {
      const fd = new FormData(form);
      const t = await api.createTeam({ name: fd.get("name"), description: fd.get("description") || null });
      toast("Equipe criada", "success");
      close();
      window.location.hash = `#/teams/${t.id}`;
    } catch (err) {
      errBox.appendChild(errorBox(err));
      submit.disabled = false;
    }
  };
}

route("/teams/:id", async ({ id }) => {
  const team = await api.getTeam(id);
  const canEdit = auth.isAdmin() || team.owner_id === auth.user.id;

  const header = el("div", { class: "page-header" },
    el("div", { class: "title" },
      el("h1", {}, team.name),
      team.is_active ? el("span", { class: "badge" }, "Ativa") : el("span", { class: "badge inactive" }, "Arquivada"),
    ),
    el("div", { class: "row" },
      canEdit ? el("button", { class: "btn", onclick: () => openEditTeamModal(team) }, "Editar") : null,
      canEdit && team.is_active ? el("button", { class: "btn btn-danger", onclick: () => archiveTeam(team.id) }, "Arquivar") : null,
    ),
  );

  const info = el("div", { class: "card" },
    el("h3", {}, "Sobre a equipe"),
    el("p", {}, team.description || "Sem descrição."),
    el("p", { class: "meta" }, "Criada em " + fmtDate(team.created_at)),
  );

  const tbl = el("div", { class: "table-wrap" },
    el("table", {},
      el("thead", {}, el("tr", {}, el("th", {}, "Usuário"), el("th", {}, "Email"), el("th", {}, "Entrou em"), el("th", {}, ""))),
      el("tbody", {}, ...(team.members || []).map(m =>
        el("tr", {},
          el("td", {}, m.username), el("td", {}, m.email), el("td", {}, fmtDate(m.joined_at)),
          el("td", {}, canEdit ? el("button", { class: "btn btn-sm btn-danger", onclick: () => removeTeamMember(team.id, m.user_id) }, "Remover") : ""),
        ),
      )),
    ),
  );

  return el("div", {}, header, info,
    el("div", { class: "page-header", style: "margin-top: 1.5rem;" },
      el("div", { class: "title" }, el("h2", {}, "Membros (" + (team.members?.length || 0) + ")")),
      canEdit ? el("button", { class: "btn btn-primary btn-sm", onclick: () => openAddTeamMemberModal(team) }, "+ Adicionar membro") : null,
    ),
    tbl,
  );
});

async function openEditTeamModal(team) {
  const form = el("form", {});
  form.appendChild(field("name", "Nome", { required: true, value: team.name }));
  form.appendChild(el("div", { class: "field" },
    el("label", { for: "f-description" }, "Descrição"),
    el("textarea", { id: "f-description", name: "description", rows: 3 }, team.description || ""),
  ));
  const errBox = el("div"); form.prepend(errBox);
  const submit = submitFor(form, "Salvar");
  const cancel = el("button", { class: "btn", type: "button" }, "Cancelar");
  const { close } = openModal({ title: "Editar equipe", body: form, footer: el("div", {}, cancel, submit) });
  cancel.onclick = close;
  form.onsubmit = async (e) => {
    e.preventDefault();
    errBox.innerHTML = "";
    submit.disabled = true;
    try {
      const fd = new FormData(form);
      await api.updateTeam(team.id, { name: fd.get("name"), description: fd.get("description") || null });
      toast("Equipe atualizada", "success");
      close();
      renderRoute();
    } catch (err) {
      errBox.appendChild(errorBox(err));
      submit.disabled = false;
    }
  };
}

async function archiveTeam(id) {
  if (!confirm("Arquivar esta equipe?")) return;
  try { await api.archiveTeam(id); toast("Equipe arquivada", "success"); window.location.hash = "#/teams"; }
  catch (err) { toast(err.message, "error"); }
}

async function removeTeamMember(teamId, userId) {
  if (!confirm("Remover este membro?")) return;
  try { await api.removeTeamMember(teamId, userId); toast("Membro removido", "success"); renderRoute(); }
  catch (err) { toast(err.message, "error"); }
}

async function openAddTeamMemberModal(team) {
  let users = [];
  try { users = await api.listUsers({ limit: 200 }); } catch {}
  const memberIds = new Set((team.members || []).map(m => m.user_id));
  const candidates = users.filter(u => !memberIds.has(u.id) && u.is_active);

  const form = el("form", {});
  const select = el("select", { name: "user_id", required: true },
    el("option", { value: "" }, "— Selecione um usuário —"),
    ...candidates.map(u => el("option", { value: u.id }, `${u.full_name || u.username} (${u.email})`)),
  );
  form.appendChild(el("div", { class: "field" }, el("label", {}, "Usuário"), select));
  const errBox = el("div"); form.prepend(errBox);
  const submit = submitFor(form, "Adicionar");
  const cancel = el("button", { class: "btn", type: "button" }, "Cancelar");
  const { close } = openModal({ title: "Adicionar membro à equipe", body: form, footer: el("div", {}, cancel, submit) });
  cancel.onclick = close;
  form.onsubmit = async (e) => {
    e.preventDefault();
    errBox.innerHTML = "";
    submit.disabled = true;
    try {
      const fd = new FormData(form);
      await api.addTeamMember(team.id, Number(fd.get("user_id")));
      toast("Membro adicionado", "success");
      close();
      renderRoute();
    } catch (err) {
      errBox.appendChild(errorBox(err));
      submit.disabled = false;
    }
  };
}

/* ============================================================
   page: USERS (admin only)
   ============================================================ */
route("/users", async () => {
  const [users, roles] = await Promise.all([api.listUsers({ limit: 200 }), api.listRoles()]);
  const rolesById = Object.fromEntries(roles.map(r => [r.id, r]));

  const header = el("div", { class: "page-header" },
    el("div", { class: "title" }, el("h1", {}, "Usuários")),
    el("button", { class: "btn btn-primary", onclick: () => openCreateUserModal(roles) }, "+ Novo usuário"),
  );

  const rows = users.map(u => {
    const role = rolesById[u.role_id];
    return el("tr", {},
      el("td", {}, el("div", { style: "display: flex; align-items: center; gap: .6rem;" },
        el("div", { class: "avatar" }, initials(u.full_name || u.username)),
        el("div", {}, el("strong", {}, u.full_name || u.username), el("div", { class: "meta" }, "@" + u.username)),
      )),
      el("td", {}, u.email),
      el("td", {}, el("span", { class: `badge role-${role?.name || ""}` }, ptRole(role?.name))),
      el("td", {}, u.is_active ? el("span", { class: "badge" }, "Ativo") : el("span", { class: "badge inactive" }, "Inativo")),
      el("td", {}, fmtDate(u.created_at)),
      el("td", {},
        el("div", { class: "row" },
          el("button", { class: "btn btn-sm", onclick: () => openEditUserModal(u, roles) }, "Editar"),
          u.is_active ? el("button", { class: "btn btn-sm btn-danger", onclick: () => deactivateUser(u.id) }, "Desativar") : null,
        ),
      ),
    );
  });

  return el("div", {}, header,
    el("div", { class: "table-wrap" },
      el("table", {},
        el("thead", {}, el("tr", {},
          el("th", {}, "Usuário"), el("th", {}, "Email"), el("th", {}, "Papel"),
          el("th", {}, "Status"), el("th", {}, "Criado em"), el("th", {}, "Ações"))),
        el("tbody", {}, ...rows),
      ),
    ),
  );
}, { adminOnly: true });

async function openCreateUserModal(roles) {
  const form = el("form", {});
  form.appendChild(field("full_name", "Nome completo"));
  form.appendChild(field("username", "Usuário", { required: true, minlength: 3 }));
  form.appendChild(field("email", "Email", { type: "email", required: true }));
  form.appendChild(field("password", "Senha", { type: "password", required: true, minlength: 8 }));
  const roleSel = el("select", { name: "role_id", required: true },
    ...roles.map(r => el("option", { value: r.id }, ptRole(r.name))),
  );
  form.appendChild(el("div", { class: "field" }, el("label", {}, "Papel"), roleSel));
  const errBox = el("div"); form.prepend(errBox);
  const submit = submitFor(form, "Criar");
  const cancel = el("button", { class: "btn", type: "button" }, "Cancelar");
  const { close } = openModal({ title: "Novo usuário", body: form, footer: el("div", {}, cancel, submit) });
  cancel.onclick = close;
  form.onsubmit = async (e) => {
    e.preventDefault();
    errBox.innerHTML = "";
    submit.disabled = true;
    try {
      const fd = new FormData(form);
      await api.createUser({
        full_name: fd.get("full_name") || null,
        username: fd.get("username"),
        email: fd.get("email"),
        password: fd.get("password"),
        role_id: Number(fd.get("role_id")),
      });
      toast("Usuário criado", "success");
      close();
      renderRoute();
    } catch (err) {
      errBox.appendChild(errorBox(err));
      submit.disabled = false;
    }
  };
}

async function openEditUserModal(user, roles) {
  const form = el("form", {});
  form.appendChild(field("full_name", "Nome completo", { value: user.full_name || "" }));
  form.appendChild(field("email", "Email", { type: "email", value: user.email }));
  const roleSel = el("select", { name: "role_id" },
    ...roles.map(r => el("option", { value: r.id, selected: r.id === user.role_id ? "" : null }, ptRole(r.name))),
  );
  form.appendChild(el("div", { class: "field" }, el("label", {}, "Papel"), roleSel));
  const activeSel = el("select", { name: "is_active" },
    el("option", { value: "true", selected: user.is_active ? "" : null }, "Ativo"),
    el("option", { value: "false", selected: !user.is_active ? "" : null }, "Inativo"),
  );
  form.appendChild(el("div", { class: "field" }, el("label", {}, "Status"), activeSel));
  const errBox = el("div"); form.prepend(errBox);
  const submit = submitFor(form, "Salvar");
  const cancel = el("button", { class: "btn", type: "button" }, "Cancelar");
  const { close } = openModal({ title: "Editar usuário", body: form, footer: el("div", {}, cancel, submit) });
  cancel.onclick = close;
  form.onsubmit = async (e) => {
    e.preventDefault();
    errBox.innerHTML = "";
    submit.disabled = true;
    try {
      const fd = new FormData(form);
      await api.updateUser(user.id, {
        full_name: fd.get("full_name") || null,
        email: fd.get("email"),
        role_id: Number(fd.get("role_id")),
        is_active: fd.get("is_active") === "true",
      });
      toast("Usuário atualizado", "success");
      close();
      renderRoute();
    } catch (err) {
      errBox.appendChild(errorBox(err));
      submit.disabled = false;
    }
  };
}

async function deactivateUser(id) {
  if (!confirm("Desativar este usuário? Ele não conseguirá mais fazer login.")) return;
  try { await api.deactivateUser(id); toast("Usuário desativado", "success"); renderRoute(); }
  catch (err) { toast(err.message, "error"); }
}

/* ============================================================
   page: PROFILE
   ============================================================ */
route("/profile", async () => {
  const me = await api.me();
  auth.set({ user: me });

  const form = el("form", {});
  form.appendChild(field("full_name", "Nome completo", { value: me.full_name || "" }));
  form.appendChild(field("email", "Email", { type: "email", value: me.email }));
  const errBox = el("div"); form.prepend(errBox);
  form.onsubmit = async (e) => {
    e.preventDefault();
    errBox.innerHTML = "";
    const btn = $("button[type=submit]", form);
    btn.disabled = true;
    try {
      const fd = new FormData(form);
      const updated = await api.updateUser(me.id, {
        full_name: fd.get("full_name") || null,
        email: fd.get("email"),
      });
      auth.set({ user: { ...me, ...updated } });
      toast("Perfil atualizado", "success");
      renderRoute();
    } catch (err) {
      errBox.appendChild(errorBox(err));
    } finally {
      btn.disabled = false;
    }
  };
  form.appendChild(el("button", { class: "btn btn-primary", type: "submit" }, "Salvar"));

  return el("div", {},
    el("div", { class: "page-header" }, el("div", { class: "title" }, el("h1", {}, "Meu perfil"))),
    el("div", { class: "card" },
      el("div", { style: "display: flex; align-items: center; gap: 1rem; margin-bottom: 1rem;" },
        el("div", { class: "avatar", style: "width: 64px; height: 64px; font-size: 1.5rem;" }, initials(me.full_name || me.username)),
        el("div", {},
          el("h2", { style: "margin: 0;" }, me.full_name || me.username),
          el("div", { class: "meta" }, "@" + me.username),
          el("span", { class: `badge role-${me.role?.name}` }, ptRole(me.role?.name)),
        ),
      ),
      form,
    ),
  );
});

/* ============================================================
   bootstrap
   ============================================================ */
(async function bootstrap() {
  // Sanity check: if we have a token, validate it (refresh user data).
  if (auth.token) {
    try {
      const me = await api.me();
      auth.set({ user: me });
    } catch {
      // me() will have triggered logout if 401
    }
  }
  if (!window.location.hash) {
    window.location.hash = auth.token ? "#/dashboard" : "#/login";
  } else {
    renderRoute();
  }
})();
