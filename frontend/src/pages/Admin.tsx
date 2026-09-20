import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import ThemeToggle from "../ThemeToggle";

export default function Admin() {
  const { logout } = useAuth();
  const params = useParams();
  const [tab, setTab] = useState(params.tab || "users");
  const [data, setData] = useState<any>([]);
  useEffect(() => {
    if (params.tab) setTab(params.tab);
  }, [params.tab]);
  useEffect(() => {
    const map: Record<string, string> = {
      users: "/admin/users",
      workspaces: "/admin/workspaces",
      campaigns: "/admin/campaigns",
      calls: "/admin/calls",
      usage: "/admin/usage",
      audit: "/admin/audit-logs",
    };
    api.get(map[tab] || map.users).then((r) => setData(r.data));
  }, [tab]);
  return (
    <div className="min-h-screen p-6">
      <div className="flex justify-between mb-6">
        <h1 className="text-2xl font-semibold">Admin</h1>
        <div className="flex gap-3 text-sm items-center">
          <ThemeToggle />
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
      <div className="card p-4 overflow-auto">
        <pre className="text-xs">{JSON.stringify(data, null, 2)}</pre>
      </div>
    </div>
  );
}
