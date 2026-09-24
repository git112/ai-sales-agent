import { useEffect, useState } from "react";
import { api, authStore } from "../api";

export default function Settings() {
  const [ws, setWs] = useState<any[]>([]);
  const [locale, setLocale] = useState(authStore.locale());
  useEffect(() => {
    api.get("/workspaces").then((r) => setWs(r.data));
  }, []);
  return (
    <div className="max-w-xl space-y-4">
      <h1 className="text-2xl font-semibold">Settings</h1>
      <div className="card p-5 bg-white shadow-xs space-y-3">
        <h2 className="font-bold text-slate-900 text-sm">Application Interface Language</h2>
        <p className="text-xs text-slate-500">Select default display and speech recognition language across all screens.</p>
        <select
          className="input h-10 max-w-sm text-xs font-medium"
          value={locale}
          onChange={(e) => {
            setLocale(e.target.value);
            authStore.setLocale(e.target.value);
          }}
        >
          <option value="en">English (US/UK/Global)</option>
          <option value="hi">Hindi (हिन्दी)</option>
          <option value="gu">Gujarati (ગુજરાતી)</option>
          <option value="es">Spanish (Español)</option>
          <option value="fr">French (Français)</option>
          <option value="de">German (Deutsch)</option>
        </select>
      </div>

      {/* CRM & Lead Sources */}
      <div className="card p-5 bg-white shadow-xs space-y-4">
        <div>
          <h2 className="font-bold text-slate-900 text-sm">CRM & External Lead Integrations</h2>
          <p className="text-xs text-slate-500 mt-0.5">Bi-directional contact syncing and automated qualified opportunity export.</p>
        </div>

        <div className="space-y-3 divide-y divide-slate-100">
          <div className="pt-2 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-orange-50 text-orange-600 flex items-center justify-center font-bold text-xs">HS</div>
              <div>
                <div className="text-xs font-bold text-slate-900">HubSpot CRM</div>
                <div className="text-[11px] text-slate-400">Two-way deal and call transcript synchronization</div>
              </div>
            </div>
            <span className="badge bg-emerald-50 text-emerald-700 border border-emerald-200">Connected</span>
          </div>

          <div className="pt-3 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center font-bold text-xs">SF</div>
              <div>
                <div className="text-xs font-bold text-slate-900">Salesforce</div>
                <div className="text-[11px] text-slate-400">Lead routing, Opportunity stages, and Activity history</div>
              </div>
            </div>
            <button className="btn btn-ghost text-xs py-1.5 px-3">Configure</button>
          </div>

          <div className="pt-3 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center font-bold text-xs">ZH</div>
              <div>
                <div className="text-xs font-bold text-slate-900">Zoho CRM</div>
                <div className="text-[11px] text-slate-400">Sync accounts, custom fields and call outcomes</div>
              </div>
            </div>
            <button className="btn btn-ghost text-xs py-1.5 px-3">Connect</button>
          </div>

          <div className="pt-3 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-violet-50 text-violet-600 flex items-center justify-center font-bold text-xs">API</div>
              <div>
                <div className="text-xs font-bold text-slate-900">Inbound Webhooks / Zapier</div>
                <div className="text-[11px] text-slate-400">Instant trigger for form leads to AI qualification call</div>
              </div>
            </div>
            <span className="badge bg-indigo-50 text-indigo-700 border border-indigo-200">Active</span>
          </div>
        </div>
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
