import { useEffect, useState } from "react";
import { api, authStore } from "../api";
import ThemeToggle from "../ThemeToggle";

export default function Settings() {
  const [ws, setWs] = useState<any[]>([]);
  const [locale, setLocale] = useState(authStore.locale());
  useEffect(() => {
    api.get("/workspaces").then((r) => setWs(r.data));
  }, []);
  return (
    <div className="max-w-xl space-y-4">
      <h1 className="text-2xl font-semibold">Settings</h1>
      <div className="card p-4">
        <h2 className="font-semibold">Appearance</h2>
        <p className="text-sm text-gray-500 mt-1">Switch light and dark without reloading.</p>
        <div className="mt-3">
          <ThemeToggle />
        </div>
      </div>
      <div className="card p-4">
        <h2 className="font-semibold">Language</h2>
        <select
          className="input mt-2"
          value={locale}
          onChange={(e) => {
            setLocale(e.target.value);
            authStore.setLocale(e.target.value);
          }}
        >
          <option value="en">English</option>
          <option value="hi">Hindi</option>
          <option value="gu">Gujarati</option>
        </select>
      </div>
      <div className="card p-4">
        <h2 className="font-semibold">Workspaces</h2>
        {ws.map((w) => (
          <div key={w.id} className="flex justify-between text-sm py-2">
            <span>
              {w.name} · {w.mode}
            </span>
            <button
              className="btn btn-ghost"
              onClick={async () => {
                const { data } = await api.post(`/workspaces/${w.id}/select`);
                authStore.setToken(data.token);
                authStore.setWorkspace(w.id);
              }}
            >
              Select
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
