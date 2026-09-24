import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Radio, Plus, Play, Pause, Bell, ArrowUpRight, Check, Search, Globe, Clock } from "lucide-react";
import { api } from "../api";

export default function Radar() {
  const [searches, setSearches] = useState<any[]>([]);
  const [notes, setNotes] = useState<any[]>([]);
  const [name, setName] = useState("SharePoint opportunities in India");
  const [query, setQuery] = useState("Companies looking for SharePoint implementation in India");
  const [frequency, setFrequency] = useState("daily");
  const [runMsg, setRunMsg] = useState("");
  const [saving, setSaving] = useState(false);

  async function load() {
    const sData = (await api.get("/saved-searches")).data;
    const nData = (await api.get("/notifications")).data;
    setSearches(sData);
    setNotes(nData);
  }

  useEffect(() => {
    load();
  }, []);

  async function saveSearch() {
    if (!name.trim() || !query.trim()) return;
    setSaving(true);
    try {
      await api.post("/saved-searches", {
        name,
        query,
        frequency,
        source: "Market Intelligence",
        status: "active"
      });
      load();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-indigo-50 text-indigo-600 border border-indigo-100">
            <Radio className="w-5 h-5" />
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Opportunity Radar</h1>
        </div>
        <p className="text-sm text-slate-500 mt-1">
          Automated radar scanners continually monitor connected web signals and dispatch notifications on new matches.
        </p>
      </div>

      {/* Query Creation Form */}
      <div className="card p-5 bg-white shadow-xs space-y-4">
        <h2 className="font-bold text-slate-900 text-sm uppercase tracking-wider flex items-center gap-2">
          <Plus className="w-4 h-4 text-indigo-600" />
          Configure New Radar Scanner
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-12 gap-3">
          <div className="md:col-span-4">
            <label className="block text-xs font-semibold text-slate-600 mb-1">Radar Target Name</label>
            <input
              className="input h-10"
              placeholder="e.g. Cloud Migration Targets"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div className="md:col-span-5">
            <label className="block text-xs font-semibold text-slate-600 mb-1">Search Intent / Natural Query</label>
            <div className="relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                className="input search-input h-10"
                placeholder="e.g. Companies requesting Azure or AWS migration"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>
          </div>
          <div className="md:col-span-2">
            <label className="block text-xs font-semibold text-slate-600 mb-1">Scan Interval</label>
            <select
              className="input h-10 text-xs font-medium"
              value={frequency}
              onChange={(e) => setFrequency(e.target.value)}
            >
              <option value="daily">Daily Scan</option>
              <option value="weekly">Weekly Scan</option>
              <option value="hourly">Hourly Scan</option>
            </select>
          </div>
          <div className="md:col-span-1 flex items-end">
            <button
              className="btn btn-primary h-10 w-full text-xs font-semibold"
              disabled={saving}
              onClick={saveSearch}
            >
              {saving ? "Saving…" : "Save"}
            </button>
          </div>
        </div>
      </div>

      {/* Active Scanners */}
      <div className="space-y-3">
        <h2 className="font-bold text-slate-900 text-base">Active Radar Scanners ({searches.length})</h2>
        {searches.map((s) => (
          <div key={s.id} className="card p-5 bg-white hover:border-slate-300 transition-all shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="font-bold text-slate-900 text-base">{s.name}</span>
                <span
                  className={`badge ${
                    s.status === "paused"
                      ? "bg-slate-100 text-slate-600 border border-slate-200"
                      : "bg-emerald-50 text-emerald-700 border border-emerald-200/80"
                  }`}
                >
                  {s.status || "active"}
                </span>
                <span className="text-xs text-slate-400">· {s.frequency}</span>
              </div>
              <div className="text-sm text-slate-600 flex items-center gap-1.5">
                <Search className="w-3.5 h-3.5 text-slate-400" />
                <span>{s.query}</span>
              </div>
              <div className="flex items-center gap-4 text-xs text-slate-400 pt-1">
                <span>Last executed: {s.last_run_at || "Awaiting scheduled run"}</span>
                <span>Matches found: <strong className="text-indigo-600">{s.new_matches ?? 0}</strong></span>
              </div>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <button
                className="btn btn-ghost text-xs py-2 px-3 flex items-center gap-1.5"
                onClick={async () => {
                  await api.patch(`/saved-searches/${s.id}`, { status: s.status === "paused" ? "active" : "paused" });
                  load();
                }}
              >
                {s.status === "paused" ? <Play className="w-3.5 h-3.5 text-emerald-600" /> : <Pause className="w-3.5 h-3.5 text-amber-600" />}
                <span>{s.status === "paused" ? "Resume" : "Pause"}</span>
              </button>
              <button
                className="btn btn-primary text-xs py-2 px-3 flex items-center gap-1.5"
                onClick={async () => {
                  const { data } = await api.post(`/saved-searches/${s.id}/run`);
                  setRunMsg(`Radar query triggered: ${data.new_matches ?? 0} new opportunities captured.`);
                  load();
                }}
              >
                <Play className="w-3.5 h-3.5" />
                <span>Scan Now</span>
              </button>
            </div>
          </div>
        ))}
      </div>

      {runMsg && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs font-semibold text-emerald-800">
          {runMsg}
        </div>
      )}

      {/* Dispatched Radar Signals */}
      <div className="space-y-3 pt-4">
        <div className="flex items-center justify-between">
          <h2 className="font-bold text-slate-900 text-base">Radar Dispatched Signals</h2>
          <Link to="/app/notifications" className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1">
            <span>View All Alerts</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {notes.slice(0, 5).map((n) => (
          <div key={n.id} className="card p-4 bg-white hover:border-slate-300 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="font-bold text-slate-900 text-sm">{n.title}</span>
                <span className="text-xs text-slate-400">· {n.detected_at?.slice(0, 10) || n.created_at?.slice(0, 10)}</span>
              </div>
              <p className="text-xs text-slate-600 max-w-2xl">{n.body}</p>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              {n.opportunity_id && (
                <Link
                  to={`/app/opportunities/${n.opportunity_id}`}
                  className="btn btn-primary text-xs py-1 px-2.5 flex items-center gap-1"
                >
                  <span>Explore</span>
                  <ArrowUpRight className="w-3.5 h-3.5" />
                </Link>
              )}
              {!n.read && (
                <button
                  className="btn btn-ghost text-xs py-1 px-2.5 text-slate-500"
                  onClick={async () => {
                    await api.post(`/notifications/${n.id}/read`);
                    load();
                  }}
                >
                  <Check className="w-3 h-3" />
                  <span>Read</span>
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
