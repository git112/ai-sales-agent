import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { api, authStore } from "../api";
import { useAuth } from "../auth";
import { t, type Locale } from "../i18n";

const nav = [
  ["Dashboard", "/app/dashboard"],
  ["Opportunities", "/app/opportunities"],
  ["Leads", "/app/leads"],
  ["Campaigns", "/app/campaigns"],
  ["Voice Agents", "/app/agents"],
  ["Calls", "/app/calls"],
  ["Tasks", "/app/tasks"],
  ["AI Copilot", "/app/copilot"],
  ["Knowledge Base", "/app/knowledge"],
  ["Radar", "/app/radar"],
  ["Analytics", "/app/analytics"],
  ["Notifications", "/app/notifications"],
  ["Settings", "/app/settings"],
];

export default function AppShell() {
  const { user, logout } = useAuth();
  const navGo = useNavigate();
  const [mode, setMode] = useState<"demo" | "live">("demo");
  const [notes, setNotes] = useState<any[]>([]);
  const locale = (authStore.locale() as Locale) || "en";

  useEffect(() => {
    api.get("/workspaces").then(({ data }) => {
      const ws = data.find((w: any) => w.id === authStore.workspaceId()) || data[0];
      if (ws) {
        setMode(ws.mode);
        authStore.setWorkspace(ws.id);
      }
    });
    api.get("/notifications").then(({ data }) => setNotes(data.filter((n: any) => !n.read)));
  }, []);

  async function toggleMode() {
    const next = mode === "demo" ? "live" : "demo";
    const id = authStore.workspaceId();
    if (!id) return;
    const form = new FormData();
    form.append("mode", next);
    await api.patch(`/workspaces/${id}/mode`, form);
    setMode(next);
  }

  return (
    <div className="min-h-screen flex">
      <aside className="w-64 border-r flex flex-col shell">
        <Link to="/" className="px-5 py-6 font-semibold flex items-center">
          <span className="logo-mark">L</span>
          <span>
            Lumina
            <div className="text-xs font-normal text-gray-500 mt-0.5">Illuminating the Signal</div>
          </span>
        </Link>
        <nav className="px-3 flex-1 space-y-0.5">
          {nav.map(([label, to]) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `block rounded-xl px-3 py-2 text-sm transition ${isActive ? "bg-blue-50 text-blue-800 font-semibold" : "text-gray-500 hover:bg-gray-50"}`
              }
            >
              {label}
            </NavLink>
          ))}
          {user?.role === "admin" && (
            <NavLink to="/admin" className="block rounded-xl px-3 py-2 text-sm text-gray-500 hover:bg-gray-50">
              Admin
            </NavLink>
          )}
        </nav>
        <div className="p-4 text-xs text-gray-500 border-t">{user?.email}</div>
      </aside>
      <div className="flex-1 min-w-0">
        <header className="h-16 border-b flex items-center justify-between px-6 shell">
          <div className="flex items-center gap-3 min-w-0">
            <span className={`badge ${mode === "demo" ? "bg-amber-50 text-amber-800" : "bg-blue-50 text-blue-800"}`}>
              {mode === "demo" ? t[locale].demo : t[locale].live}
            </span>
            <button className="btn btn-ghost text-xs" onClick={toggleMode}>
              Switch to {mode === "demo" ? "LIVE" : "DEMO"}
            </button>
            {notes[0] && (
              <Link to="/app/notifications" className="text-sm text-gray-500 truncate">
                {notes.filter((n) => !n.read).length} new · {notes[0].title}
              </Link>
            )}
          </div>
          <div className="flex items-center gap-3 text-sm">
            <Link to="/app/onboarding" className="text-gray-500">
              Onboarding
            </Link>
            <button
              className="text-gray-500"
              onClick={async () => {
                await logout();
                navGo("/");
              }}
            >
              Logout
            </button>
          </div>
        </header>
        {mode === "live" && (
          <div className="bg-blue-50 text-blue-900 text-sm px-6 py-2 border-b">
            LIVE MODE is selected. Telephony is not configured — calling stays in Demo Voice Simulation unless providers are added.
          </div>
        )}
        {mode === "demo" && (
          <div className="bg-amber-50 text-amber-900 text-sm px-6 py-2 border-b">
            DEMO MODE — seeded records are labeled DEMO DATA. Simulated calls are never presented as live telephony.
          </div>
        )}
        <main className="p-7">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
