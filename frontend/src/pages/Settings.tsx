import { useEffect, useState } from "react";
import { PhoneCall, ShieldCheck, ShieldOff, RefreshCw, Settings as SettingsIcon } from "lucide-react";
import { api, authStore } from "../api";

export default function Settings() {
  const [ws, setWs] = useState<any[]>([]);
  const [active, setActive] = useState<any>(null);
  const [locale, setLocale] = useState(authStore.locale());
  const [bolna, setBolna] = useState<any>(null);
  const [phone, setPhone] = useState("");
  const [savingPhone, setSavingPhone] = useState(false);
  const [switchingMode, setSwitchingMode] = useState(false);
  const [phoneMsg, setPhoneMsg] = useState("");
  const [modeMsg, setModeMsg] = useState("");

  const refresh = async () => {
    const { data } = await api.get("/workspaces");
    setWs(data);
    const selected = authStore.workspaceId();
    const current = data.find((w: any) => w.id === selected) || data[0];
    setActive(current || null);
    setPhone(current?.from_phone_number || "");
    try {
      const { data: h } = await api.get("/bolna/health");
      setBolna(h);
    } catch {
      setBolna(null);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const switchMode = async (mode: "demo" | "live") => {
    if (!active) return;
    setSwitchingMode(true);
    setModeMsg("");
    try {
      const fd = new FormData();
      fd.append("mode", mode);
      await api.patch(`/workspaces/${active.id}/mode`, fd);
      setModeMsg(`Switched to ${mode.toUpperCase()} mode.`);
      await refresh();
    } catch (e: any) {
      setModeMsg(e.userMessage || "Failed to switch mode");
    } finally {
      setSwitchingMode(false);
    }
  };

  const savePhone = async () => {
    if (!active) return;
    setSavingPhone(true);
    setPhoneMsg("");
    try {
      await api.patch(`/workspaces/${active.id}/phone`, { from_phone_number: phone || null });
      setPhoneMsg("Saved.");
      await refresh();
    } catch (e: any) {
      setPhoneMsg(e.userMessage || "Failed to save");
    } finally {
      setSavingPhone(false);
    }
  };

  return (
    <div className="max-w-3xl space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-indigo-50 text-indigo-600 border border-indigo-100">
            <SettingsIcon className="w-5 h-5" />
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Workspace Settings</h1>
        </div>
        <p className="text-sm text-slate-500 mt-1">
          Manage workspace telephony, language preferences, and CRM integration parameters.
        </p>
      </div>
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

      {/* Live Calling (Bolna) */}
      {active && (
        <div className="card p-5 bg-white shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="p-1.5 rounded-lg bg-indigo-50 text-indigo-600">
                <PhoneCall className="w-4 h-4" />
              </div>
              <div>
                <h2 className="font-bold text-slate-900 text-sm">Live Calling (Bolna)</h2>
                <p className="text-[11px] text-slate-500">
                  Real outbound calls via Bolna Voice AI. Multilingual agent (en/hi/gu/es/fr/de) with mid-call language switching.
                </p>
              </div>
            </div>
            <button className="btn btn-ghost text-xs py-1.5 px-2" onClick={refresh}>
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              {bolna?.configured ? (
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
              ) : (
                <ShieldOff className="w-4 h-4 text-slate-400" />
              )}
              <span className={bolna?.configured ? "text-emerald-700 font-semibold" : "text-slate-500"}>
                {bolna?.configured
                  ? `Connected · ${bolna.user?.email || bolna.user?.name || "Bolna account"}`
                  : "BOLNA_API_KEY not configured on server"}
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <button
                className={`btn text-xs py-1.5 px-3 ${active.mode === "demo" ? "btn-primary" : "btn-ghost"}`}
                disabled={switchingMode}
                onClick={() => switchMode("demo")}
              >
                Demo
              </button>
              <button
                className={`btn text-xs py-1.5 px-3 ${active.mode === "live" ? "btn-primary" : "btn-ghost"}`}
                disabled={switchingMode || !bolna?.configured}
                onClick={() => switchMode("live")}
              >
                Live
              </button>
            </div>
          </div>
          {modeMsg && <p className="text-[11px] text-slate-600">{modeMsg}</p>}

          <div className="space-y-2 pt-2">
            <label className="block text-xs font-semibold text-slate-700">Outbound caller ID (from_phone_number)</label>
            <div className="flex items-center gap-2">
              <input
                className="input h-10 text-xs font-medium flex-1"
                placeholder="+15551234567"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
              />
              <button
                className="btn btn-primary text-xs py-2 px-3"
                disabled={savingPhone}
                onClick={savePhone}
              >
                {savingPhone ? "Saving…" : "Save"}
              </button>
            </div>
            <p className="text-[11px] text-slate-400">
              E.164 format (e.g. +14155550123). Use a Bolna-hosted number from your wallet, or leave blank to let Bolna pick the default outbound number.
            </p>
            {phoneMsg && <p className="text-[11px] text-slate-600">{phoneMsg}</p>}
          </div>
        </div>
      )}

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
      <div className="card p-5 bg-white shadow-xs space-y-3">
        <h2 className="font-bold text-slate-900 text-sm">Tenant Workspaces</h2>
        <p className="text-xs text-slate-500">Switch active workspace environment context.</p>
        <div className="divide-y divide-slate-100">
          {ws.map((w) => (
            <div key={w.id} className="flex items-center justify-between text-sm py-3">
              <div>
                <span className="font-semibold text-slate-800">{w.name}</span>
                <span className="ml-2 text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 font-medium uppercase">{w.mode}</span>
              </div>
              <button
                className="btn btn-ghost text-xs px-3 py-1.5"
                onClick={async () => {
                  const { data } = await api.post(`/workspaces/${w.id}/select`);
                  authStore.setToken(data.token);
                  authStore.setWorkspace(w.id);
                  await refresh();
                }}
              >
                Select
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
