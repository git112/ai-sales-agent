import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Search, Users, Download, Upload, Filter, Layers, ArrowUpRight, X } from "lucide-react";
import { api } from "../api";

const stages = ["discovered", "reviewed", "contacted", "qualified", "meeting", "proposal", "won", "lost"];

const stageColors: Record<string, string> = {
  discovered: "bg-slate-100 text-slate-700 border-slate-200",
  reviewed: "bg-blue-50 text-blue-700 border-blue-200",
  contacted: "bg-amber-50 text-amber-700 border-amber-200",
  qualified: "bg-emerald-50 text-emerald-700 border-emerald-200",
  meeting: "bg-indigo-50 text-indigo-700 border-indigo-200",
  proposal: "bg-violet-50 text-violet-700 border-violet-200",
  won: "bg-teal-50 text-teal-700 border-teal-200",
  lost: "bg-rose-50 text-rose-700 border-rose-200",
};

export default function Leads() {
  const [rows, setRows] = useState<any[]>([]);
  const [q, setQ] = useState("");
  const [stage, setStage] = useState("");
  const [pipe, setPipe] = useState<any>({});
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const params: any = {};
      if (q) params.q = q;
      if (stage) params.stage = stage;
      const { data } = await api.get("/leads", { params });
      setRows(data);
      setPipe((await api.get("/leads/pipeline")).data);
    } finally {
      setLoading(false);
    }
  }

  async function download(format: string) {
    const res = await api.get("/leads/export", { params: { format, q, stage }, responseType: "blob" });
    const url = URL.createObjectURL(res.data);
    const a = document.createElement("a");
    a.href = url;
    a.download = format === "xlsx" ? "leads.xlsx" : "leads.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-indigo-50 text-indigo-600 border border-indigo-100">
              <Users className="w-5 h-5" />
            </div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Leads & Prospects</h1>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Manage, filter, and track sales pipeline qualification across discovered prospects.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <Link className="btn btn-ghost text-xs py-2 px-3 flex items-center gap-1.5" to="/app/leads/import">
            <Upload className="w-3.5 h-3.5 text-slate-500" />
            <span>Import</span>
          </Link>
          <Link className="btn btn-ghost text-xs py-2 px-3 flex items-center gap-1.5" to="/app/leads/segments">
            <Layers className="w-3.5 h-3.5 text-slate-500" />
            <span>Segments</span>
          </Link>
          <button className="btn btn-ghost text-xs py-2 px-3 flex items-center gap-1.5" onClick={() => download("csv")}>
            <Download className="w-3.5 h-3.5 text-slate-500" />
            <span>CSV</span>
          </button>
          <button className="btn btn-ghost text-xs py-2 px-3 flex items-center gap-1.5" onClick={() => download("xlsx")}>
            <Download className="w-3.5 h-3.5 text-slate-500" />
            <span>Excel</span>
          </button>
        </div>
      </div>

      {/* Consistent Search & Filters Bar */}
      <div className="card p-3 bg-white shadow-xs">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              className="input search-input h-11 pr-10"
              placeholder="Search companies, contacts, industries..."
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") load();
              }}
            />
            {q && (
              <button
                type="button"
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 p-1 rounded-md transition-colors"
                onClick={() => {
                  setQ("");
                  // trigger reload if needed or let user press enter
                }}
                title="Clear search"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          <div className="w-full sm:w-48">
            <select
              className="input h-11 text-xs font-medium"
              value={stage}
              onChange={(e) => setStage(e.target.value)}
            >
              <option value="">All Stages</option>
              {stages.map((s) => (
                <option key={s} value={s}>
                  {s.charAt(0).toUpperCase() + s.slice(1)}
                </option>
              ))}
            </select>
          </div>

          <button className="btn btn-primary h-10 px-5 text-xs font-semibold" onClick={load} disabled={loading}>
            <Filter className="w-3.5 h-3.5" />
            <span>Filter</span>
          </button>
        </div>
      </div>

      {/* Pipeline Stage Badges */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2">
        {stages.map((s) => {
          const count = (pipe[s] || []).length;
          const isSelected = stage === s;
          return (
            <button
              key={s}
              onClick={() => {
                const next = stage === s ? "" : s;
                setStage(next);
              }}
              className={`card p-3 text-left transition-all cursor-pointer ${
                isSelected
                  ? "ring-2 ring-indigo-600 bg-indigo-50/40 border-indigo-300"
                  : "bg-white hover:border-slate-300"
              }`}
            >
              <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider truncate">{s}</div>
              <div className="text-xl font-bold text-slate-900 mt-1">{count}</div>
            </button>
          );
        })}
      </div>

      {/* Leads Table */}
      <div className="card overflow-hidden bg-white shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wider bg-slate-50/80 border-b border-slate-200">
              <tr>
                <th className="p-4">Company</th>
                <th className="p-4">Contact</th>
                <th className="p-4">Stage</th>
                <th className="p-4">Score</th>
                <th className="p-4">Intent</th>
                <th className="p-4">Source</th>
                <th className="p-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.length === 0 ? (
                <tr>
                  <td colSpan={7} className="p-8 text-center text-slate-400">
                    No leads found matching your criteria.
                  </td>
                </tr>
              ) : (
                rows.map((l) => (
                  <tr key={l.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="p-4 font-semibold text-slate-900">
                      <Link className="hover:text-indigo-600 transition flex items-center gap-1.5" to={`/app/leads/${l.id}`}>
                        {l.company}
                      </Link>
                    </td>
                    <td className="p-4 text-slate-600">{l.name || "—"}</td>
                    <td className="p-4">
                      <span className={`badge border ${stageColors[l.pipeline_stage] || "bg-slate-100 text-slate-700"}`}>
                        {l.pipeline_stage}
                      </span>
                    </td>
                    <td className="p-4">
                      <span className="font-bold text-indigo-600">{l.opportunity_score ?? "—"}</span>
                    </td>
                    <td className="p-4">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                          l.intent_level === "high"
                            ? "bg-amber-100 text-amber-800 font-semibold"
                            : "text-slate-600 bg-slate-100"
                        }`}
                      >
                        {l.intent_level || "Standard"}
                      </span>
                    </td>
                    <td className="p-4 text-slate-500 text-xs">{l.source}</td>
                    <td className="p-4 text-right">
                      <Link
                        to={`/app/leads/${l.id}`}
                        className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-600 hover:text-indigo-800"
                      >
                        <span>View</span>
                        <ArrowUpRight className="w-3.5 h-3.5" />
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
