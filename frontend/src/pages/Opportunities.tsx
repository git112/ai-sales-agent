import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Search, Sparkles, Target, ArrowUpRight, Globe, Calendar, ShieldCheck, CheckCircle2, X, UserPlus, Check } from "lucide-react";
import { api } from "../api";


export default function Opportunities() {
  const nav = useNavigate();
  const [q, setQ] = useState("Find companies looking for SharePoint implementation.");
  const [rows, setRows] = useState<any[]>([]);
  const [note, setNote] = useState("");
  const [sources, setSources] = useState<any[]>([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [addingLead, setAddingLead] = useState<string | null>(null);
  const [addedLeads, setAddedLeads] = useState<Record<string, string>>({});


  async function load() {
    const { data } = await api.get("/opportunities");
    setRows(data);
  }
  useEffect(() => {
    load();
  }, []);

  async function search() {
    if (!q.trim()) return;
    setBusy(true);
    setErr("");
    try {
      const { data } = await api.post("/opportunities/search", { query: q });
      setNote(data.source_note);
      setSources(data.sources || []);
      setRows(data.results);
    } catch (e: any) {
      setErr(e.response?.data?.error?.message || "Search failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleAddLead(oppId: string, e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    setAddingLead(oppId);
    try {
      const { data } = await api.post(`/opportunities/${oppId}/add-lead`);
      setAddedLeads((prev) => ({ ...prev, [oppId]: data.lead.id }));
    } catch (err: any) {
      alert(err.response?.data?.error?.message || "Failed to add lead");
    } finally {
      setAddingLead(null);
    }
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-indigo-50 text-indigo-600 border border-indigo-100">
              <Target className="w-5 h-5" />
            </div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Opportunity Discovery</h1>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Autonomous natural language intelligence across verified enterprise feeds and signal streams.
          </p>
        </div>
      </div>

      {/* Consistent Search Bar */}
      <div className="card p-3 bg-white shadow-xs">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              className="input search-input h-12 text-sm pr-10"
              placeholder="Search by intent, technology, company need..."
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") search();
              }}
            />
            {q && (
              <button
                type="button"
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 p-1 rounded-md transition-colors"
                onClick={() => setQ("")}
                title="Clear search"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
          <button className="btn btn-primary h-12 px-6 font-semibold" disabled={busy} onClick={search}>
            {busy ? (
              <span className="flex items-center gap-2">
                <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                Discovering…
              </span>
            ) : (
              <span className="flex items-center gap-1.5">
                <Sparkles className="w-4 h-4" />
                Find Opportunities
              </span>
            )}
          </button>
        </div>
        {err && <p className="text-sm text-rose-600 mt-2 font-medium">{err}</p>}
      </div>

      {sources.length > 0 && (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
          {sources.map((s) => (
            <div key={s.name} className="card p-3.5 text-xs bg-white space-y-1">
              <div className="flex items-center justify-between">
                <div className="font-semibold text-slate-800 flex items-center gap-1.5">
                  <Globe className="w-3.5 h-3.5 text-indigo-600" />
                  {s.name}
                </div>
                <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${s.error ? "text-amber-700 bg-amber-50" : "text-emerald-700 bg-emerald-50"}`}>
                  {s.error ? "Sync Alert" : "Connected"}
                </span>
              </div>
              <div className="text-slate-500">Discovered: {s.discovered ?? "—"} matches</div>
              <div className="text-slate-400 text-[11px]">Synced: {s.last_fetched_at || "Live"}</div>
            </div>
          ))}
        </div>
      )}

      {/* Opportunities List */}
      <div className="space-y-3">
        {rows.length === 0 ? (
          <div className="card p-12 text-center text-slate-500 bg-white border border-slate-200/80 shadow-xs">
            <div className="w-12 h-12 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center mx-auto mb-3">
              <Target className="w-6 h-6" />
            </div>
            <h3 className="text-base font-bold text-slate-800">No opportunities found for &ldquo;{q}&rdquo;</h3>
            <p className="text-sm text-slate-500 mt-1.5 max-w-md mx-auto leading-relaxed">
              The signal feeds currently monitor <strong>SharePoint</strong>, <strong>Microsoft 365</strong>, <strong>cloud migration</strong>, and <strong>intranet</strong> requirements.
            </p>
            <div className="mt-4 flex items-center justify-center gap-2">
              <button
                className="btn btn-ghost text-xs"
                onClick={() => {
                  setQ("SharePoint");
                  search();
                }}
              >
                Search &ldquo;SharePoint&rdquo;
              </button>
              <button
                className="btn btn-primary text-xs"
                onClick={() => {
                  setQ("");
                  load();
                }}
              >
                Show All Opportunities
              </button>
            </div>
          </div>
        ) : (
          rows.map((o) => (
            <Link
              key={o.id}
              to={`/app/opportunities/${o.id}`}
              className="card p-5 block bg-white hover:border-indigo-200 transition-all hover:shadow-md group"
            >
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="space-y-2 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-base font-bold text-slate-900 group-hover:text-indigo-600 transition">
                      {o.company_name || o.title || o.requirement}
                    </span>
                    <span className="badge bg-indigo-50 text-indigo-700 border border-indigo-200/80">
                      <CheckCircle2 className="w-3 h-3 text-indigo-600" />
                      {o.label || "Verified Signal"}
                    </span>
                  </div>

                  <p className="text-sm text-slate-600 leading-relaxed max-w-3xl">
                    {o.requirement || o.description}
                  </p>

                  <div className="flex items-center gap-4 text-xs text-slate-400 flex-wrap pt-1">
                    <div className="flex items-center gap-1">
                      <Globe className="w-3.5 h-3.5 text-slate-400" />
                      <span className="font-medium text-slate-600">Source:</span> {o.source || o.adapter}
                    </div>
                    <div className="flex items-center gap-1">
                      <Calendar className="w-3.5 h-3.5 text-slate-400" />
                      <span className="font-medium text-slate-600">Detected:</span> {o.detected_at?.slice(0, 10) || o.published_at?.slice(0, 10) || "Recent"}
                    </div>
                    {o.confidence && (
                      <div className="flex items-center gap-1">
                        <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                        <span className="font-medium text-slate-600">Confidence:</span> {Math.round(o.confidence * 100)}%
                      </div>
                    )}
                  </div>
                </div>

                {/* Score badge + Add Lead */}
                <div className="flex md:flex-col items-center md:items-end justify-between md:justify-center border-t md:border-t-0 md:border-l border-slate-100 pt-3 md:pt-0 md:pl-6 shrink-0 gap-3">
                  <div className="text-center md:text-right">
                    <div className="text-2xl font-extrabold text-indigo-600">{o.score?.total ?? "—"}</div>
                    <div className="text-[11px] font-medium text-slate-400">Opportunity Score</div>
                  </div>
                  {addedLeads[o.id] ? (
                    <button
                      className="flex items-center gap-1.5 text-xs font-semibold text-emerald-600 bg-emerald-50 border border-emerald-200 px-3 py-1.5 rounded-lg"
                      onClick={(e) => { e.preventDefault(); nav(`/app/leads/${addedLeads[o.id]}`); }}
                    >
                      <Check className="w-3.5 h-3.5" /> View Lead
                    </button>
                  ) : (
                    <button
                      className="flex items-center gap-1.5 text-xs font-semibold text-indigo-600 bg-indigo-50 border border-indigo-200 px-3 py-1.5 rounded-lg hover:bg-indigo-100 transition disabled:opacity-60"
                      disabled={addingLead === o.id}
                      onClick={(e) => handleAddLead(o.id, e)}
                    >
                      {addingLead === o.id ? (
                        <span className="w-3.5 h-3.5 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
                      ) : (
                        <UserPlus className="w-3.5 h-3.5" />
                      )}
                      Add to Leads
                    </button>
                  )}
                  <div className="text-xs font-semibold text-indigo-600 flex items-center gap-1 group-hover:translate-x-0.5 transition">
                    <span>View Details</span>
                    <ArrowUpRight className="w-3.5 h-3.5" />
                  </div>
                </div>
              </div>
            </Link>
          ))
        )}
      </div>
    </div>
  );
}
