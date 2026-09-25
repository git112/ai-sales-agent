import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Shield, ArrowLeft, LogOut, Users, Building, Megaphone, PhoneCall, Activity, FileText } from "lucide-react";
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

  const tabs = [
    { id: "users", label: "Users", icon: Users },
    { id: "workspaces", label: "Workspaces", icon: Building },
    { id: "campaigns", label: "Campaigns", icon: Megaphone },
    { id: "calls", label: "Calls", icon: PhoneCall },
    { id: "usage", label: "Usage", icon: Activity },
    { id: "audit", label: "Audit Logs", icon: FileText },
  ];

  return (
    <div className="min-h-screen bg-slate-50/50 p-6 sm:p-8">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Top Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-5">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-indigo-50 text-indigo-600 border border-indigo-100">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-900 tracking-tight font-display">System Administration</h1>
              <p className="text-xs text-slate-500 mt-0.5">Global tenant oversight, user access governance, and usage telemetry</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Link to="/app/dashboard" className="btn btn-ghost text-xs py-2 px-3 flex items-center gap-1.5">
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Back to App</span>
            </Link>
            <button onClick={() => logout()} className="btn btn-danger text-xs py-2 px-3 flex items-center gap-1.5">
              <LogOut className="w-3.5 h-3.5" />
              <span>Log out</span>
            </button>
          </div>
        </div>

        {/* Tab Pills */}
        <div className="flex flex-wrap gap-2">
          {tabs.map((t) => {
            const Icon = t.icon;
            const active = tab === t.id;
            return (
              <Link
                key={t.id}
                to={`/admin/${t.id}`}
                className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold transition-all ${
                  active
                    ? "bg-indigo-600 text-white shadow-xs"
                    : "bg-white border border-slate-200 text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                }`}
                onClick={() => setTab(t.id)}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{t.label}</span>
              </Link>
            );
          })}
        </div>

        {err && <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs font-medium text-rose-700">{err}</div>}

        {/* Tab Content */}
        {tab === "users" && Array.isArray(data) && (
          <div className="card overflow-hidden bg-white shadow-xs">
            <div className="p-4 border-b border-slate-100 flex items-center justify-between">
              <h2 className="font-bold text-slate-900 text-sm">System Users ({data.length})</h2>
            </div>
            <div className="divide-y divide-slate-100">
              {data.map((u: any) => (
                <div key={u.id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-50/50 transition">
                  <div className="space-y-0.5">
                    <div className="text-sm font-semibold text-slate-900">{u.email}</div>
                    <div className="flex items-center gap-2 text-xs text-slate-500">
                      <span className="capitalize font-medium">{u.role}</span>
                      <span>·</span>
                      <span className={`badge ${u.status === "suspended" ? "bg-rose-50 text-rose-700 border border-rose-200" : "bg-emerald-50 text-emerald-700 border border-emerald-200"}`}>
                        {u.status || "active"}
                      </span>
                    </div>
                  </div>
                  <button
                    className={`btn text-xs py-1.5 px-3 ${u.status === "suspended" ? "btn-primary" : "btn-ghost text-rose-600 hover:bg-rose-50"}`}
                    onClick={async () => {
                      const next = (u.status || "active") === "suspended" ? "active" : "suspended";
                      await api.post(`/admin/users/${u.id}/status`, {}, { params: { status: next } });
                      load("users");
                    }}
                  >
                    {(u.status || "active") === "suspended" ? "Activate User" : "Suspend Access"}
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {tab === "campaigns" && Array.isArray(data) && (
          <div className="card overflow-hidden bg-white shadow-xs">
            <div className="p-4 border-b border-slate-100 flex items-center justify-between">
              <h2 className="font-bold text-slate-900 text-sm">Global Campaigns ({data.length})</h2>
            </div>
            <div className="divide-y divide-slate-100">
              {data.map((c: any) => (
                <div key={c.id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-50/50 transition">
                  <div className="space-y-0.5">
                    <div className="text-sm font-semibold text-slate-900">{c.name}</div>
                    <div className="text-xs text-slate-500">
                      Status: <span className="font-semibold text-slate-700 capitalize">{c.status}</span>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button className="btn btn-ghost text-xs py-1.5 px-3" onClick={async () => { await api.post(`/admin/campaigns/${c.id}/pause`); load("campaigns"); }}>
                      Pause
                    </button>
                    <button className="btn btn-primary text-xs py-1.5 px-3" onClick={async () => { await api.post(`/admin/campaigns/${c.id}/resume`); load("campaigns"); }}>
                      Resume
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {tab !== "users" && tab !== "campaigns" && (
          <div className="card p-5 bg-white shadow-xs overflow-auto">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Raw Telemetry Dump</div>
            <pre className="text-xs font-mono text-slate-800 bg-slate-50 p-4 rounded-xl border border-slate-200 overflow-x-auto max-h-[600px]">
              {JSON.stringify(data, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
