import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api, authStore } from "./api";

type User = {
  id: string;
  name: string;
  email: string;
  role: string;
  workspace_id?: string | null;
  locale?: string;
};

type AuthCtx = {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<User>;
  signup: (name: string, email: string, password: string) => Promise<User>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
};

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    if (!authStore.token()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const { data } = await api.get("/auth/me");
      setUser(data);
      if (data.workspace_id) authStore.setWorkspace(data.workspace_id);
    } catch {
      authStore.clear();
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const value = useMemo<AuthCtx>(
    () => ({
      user,
      loading,
      refresh,
      login: async (email, password) => {
        const { data } = await api.post("/auth/login", { email, password });
        authStore.setToken(data.token);
        if (data.user.workspace_id) {
          authStore.setWorkspace(data.user.workspace_id);
        } else if (data.user.role === "admin") {
          const { data: workspaces } = await api.get("/workspaces");
          if (workspaces?.[0]?.id) authStore.setWorkspace(workspaces[0].id);
        }
        setUser(data.user);
        return data.user;
      },
      signup: async (name, email, password) => {
        const { data } = await api.post("/auth/signup", { name, email, password });
        authStore.setToken(data.token);
        if (data.workspace?.id) authStore.setWorkspace(data.workspace.id);
        setUser(data.user);
        return data.user;
      },
      logout: async () => {
        try {
          await api.post("/auth/logout");
        } catch {
          /* demo logout is local */
        }
        authStore.clear();
        setUser(null);
      },
    }),
    [user, loading]
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("auth");
  return ctx;
}
