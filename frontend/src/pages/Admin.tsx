import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";

export default function Admin() {
  const { logout } = useAuth();
  const params = useParams();
  const [tab, setTab] = useState(params.tab || "users");
  const [data, setData] = useState<any>([]);
  const [err, setErr] = useState("");
  useEffect(() => {
    if (params.tab) setTab(params.tab);
  }, [params.tab]);
  async function load(t = tab) {
    const map: Record<string, string> = {
      users: "/admin/users",
      workspaces: "/admin/workspaces",
      campaigns: "/admin/campaigns",
      calls: "/admin/calls",
      usage: "/admin/usage",
      audit: "/admin/audit-logs",
    };
    setErr("");
    try {
      const r = await api.get(map[t] || map.users);
      setData(r.data);
    } catch (e: any) {
      setData([]);
      setErr(e.response?.data?.error?.message || e.message || "Admin request failed");
    }
  }
  useEffect(() => {
    load();
  }, [tab]);

  return (
    <div className="min-h-screen p-6">
      <div className="flex justify-between mb-6">
        <h1 className="text-2xl font-semibold">Admin</h1>
        <div className="flex gap-3 text-sm items-center">
          <Link to="/app/dashboard">App</Link>
          <button onClick={() => logout()}>Logout</button>
        </div>
      </div>
      <div className="flex gap-2 mb-4">
        {["users", "workspaces", "campaigns", "calls", "usage", "audit"].map((t) => (
          <Link key={t} to={`/admin/${t}`} className={`btn ${tab === t ? "btn-primary" : "btn-ghost"}`} onClick={() => setTab(t)}>
            {t}
          </Link>
        ))}
      </div>
      {err && <p className="text-sm text-red-500 mb-3">{err}</p>}
      {tab === "users" && Array.isArray(data) && (
        <div className="space-y-2">
          {data.map((u: any) => (
            <div key={u.id} className="card p-4 flex justify-between text-sm">
              <div>
                {u.email} · {u.role} · {u.status || "active"}
              </div>
              <button
                className="btn btn-ghost"
                onClick={async () => {
                  const next = (u.status || "active") === "suspended" ? "active" : "suspended";
                  await api.post(`/admin/users/${u.id}/status`, {}, { params: { status: next } });
                  load("users");
                }}
              >
                {(u.status || "active") === "suspended" ? "Activate" : "Suspend"}
              </button>
            </div>
          ))}
        </div>
      )}
      {tab === "campaigns" && Array.isArray(data) && (
        <div className="space-y-2">
          {data.map((c: any) => (
            <div key={c.id} className="card p-4 flex justify-between text-sm">
              <div>
                {c.name} · {c.status}
              </div>
              <div className="flex gap-2">
                <button className="btn btn-ghost" onClick={async () => { await api.post(`/admin/campaigns/${c.id}/pause`); load("campaigns"); }}>
                  Pause
                </button>
                <button className="btn btn-ghost" onClick={async () => { await api.post(`/admin/campaigns/${c.id}/resume`); load("campaigns"); }}>
                  Resume
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
      {tab !== "users" && tab !== "campaigns" && (
        <div className="card p-4 overflow-auto">
          <pre className="text-xs">{JSON.stringify(data, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}
