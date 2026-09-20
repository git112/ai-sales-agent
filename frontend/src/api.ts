import axios from "axios";

const TOKEN_KEY = "lumina_token";
const WS_KEY = "lumina_workspace";
const LOCALE_KEY = "lumina_locale";

export const api = axios.create({ baseURL: "/api/v1" });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  const ws = localStorage.getItem(WS_KEY);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  if (ws) config.headers["X-Workspace-Id"] = ws;
  return config;
});

export const authStore = {
  token: () => localStorage.getItem(TOKEN_KEY),
  setToken: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(WS_KEY);
  },
  workspaceId: () => localStorage.getItem(WS_KEY),
  setWorkspace: (id: string) => localStorage.setItem(WS_KEY, id),
  locale: () => localStorage.getItem(LOCALE_KEY) || "en",
  setLocale: (l: string) => localStorage.setItem(LOCALE_KEY, l),
};
