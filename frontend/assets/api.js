// Thin wrapper around fetch() with auth, error normalization, and timeouts.

const TOKEN_KEY = "auth_token";
const USER_KEY = "auth_user";
const DEFAULT_TIMEOUT = 15000;

export const auth = {
  get token() { return localStorage.getItem(TOKEN_KEY); },
  get user() {
    const raw = localStorage.getItem(USER_KEY);
    try { return raw ? JSON.parse(raw) : null; } catch { return null; }
  },
  set({ access_token, user }) {
    if (access_token) localStorage.setItem(TOKEN_KEY, access_token);
    if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },
  isAdmin() { return this.user?.role?.name === "admin"; },
  isManager() { return ["admin", "manager"].includes(this.user?.role?.name); },
};

export class ApiError extends Error {
  constructor(message, status, body) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

async function request(method, path, { body, query, timeout = DEFAULT_TIMEOUT } = {}) {
  const url = new URL(path, window.location.origin);
  if (query) {
    for (const [k, v] of Object.entries(query)) {
      if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, v);
    }
  }

  const headers = { "Accept": "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (auth.token) headers["Authorization"] = `Bearer ${auth.token}`;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);

  let res;
  try {
    res = await fetch(url, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
  } catch (err) {
    clearTimeout(timer);
    if (err.name === "AbortError") {
      throw new ApiError("Tempo de resposta excedido. Tente novamente.", 0);
    }
    throw new ApiError("Falha de rede. Verifique sua conexão.", 0);
  }
  clearTimeout(timer);

  if (res.status === 204) return null;

  let payload = null;
  const text = await res.text();
  if (text) {
    try { payload = JSON.parse(text); } catch { payload = { detail: text }; }
  }

  if (!res.ok) {
    if (res.status === 401 && auth.token) {
      // Token rejeitado — limpa sessão e força login
      auth.clear();
      window.location.hash = "#/login";
    }
    const msg = payload?.detail || `Erro ${res.status}`;
    throw new ApiError(typeof msg === "string" ? msg : JSON.stringify(msg), res.status, payload);
  }
  return payload;
}

export const api = {
  get: (p, opts) => request("GET", p, opts),
  post: (p, body, opts) => request("POST", p, { ...opts, body }),
  put: (p, body, opts) => request("PUT", p, { ...opts, body }),
  del: (p, opts) => request("DELETE", p, opts),

  // --- Auth ---
  login: (username_or_email, password) => api.post("/api/auth/login", { username_or_email, password }),
  register: (data) => api.post("/api/auth/register", data),
  me: () => api.get("/api/auth/me"),

  // --- Users / Roles ---
  listUsers: (params) => api.get("/api/users/", { query: params }),
  getUser: (id) => api.get(`/api/users/${id}`),
  createUser: (data) => api.post("/api/users/", data),
  updateUser: (id, data) => api.put(`/api/users/${id}`, data),
  deactivateUser: (id) => api.del(`/api/users/${id}`),
  listRoles: () => api.get("/api/users/roles/list"),

  // --- Teams ---
  listTeams: (params) => api.get("/api/teams/", { query: params }),
  getTeam: (id) => api.get(`/api/teams/${id}`),
  createTeam: (data) => api.post("/api/teams/", data),
  updateTeam: (id, data) => api.put(`/api/teams/${id}`, data),
  archiveTeam: (id) => api.del(`/api/teams/${id}`),
  addTeamMember: (teamId, userId) => api.post(`/api/teams/${teamId}/members/${userId}`),
  removeTeamMember: (teamId, userId) => api.del(`/api/teams/${teamId}/members/${userId}`),

  // --- Projects ---
  listProjects: (params) => api.get("/api/projects/", { query: params }),
  getProject: (id) => api.get(`/api/projects/${id}`),
  createProject: (data) => api.post("/api/projects/", data),
  updateProject: (id, data) => api.put(`/api/projects/${id}`, data),
  archiveProject: (id) => api.del(`/api/projects/${id}`),
  addProjectMember: (projectId, userId, role) =>
    api.post(`/api/projects/${projectId}/members/${userId}`, undefined, { query: { role } }),
  removeProjectMember: (projectId, userId) => api.del(`/api/projects/${projectId}/members/${userId}`),

  // --- Recommendations / activities ---
  myRecommendations: (top_k = 5) => api.get("/api/recommendations/me", { query: { top_k } }),
  logActivity: (data) => api.post("/api/recommendations/activities", data),

  // --- Integration (URLs of sibling modules) ---
  integrationConfig: () => api.get("/api/integration/config"),
  health: () => api.get("/health"),
};
