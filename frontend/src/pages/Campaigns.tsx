import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Megaphone, Plus, Search, Calendar, Globe, ArrowUpRight, CheckCircle2, X } from "lucide-react";
import { api } from "../api";

export default function Campaigns() {
  const [rows, setRows] = useState<any[]>([]);
  const [q, setQ] = useState("");

  useEffect(() => {
    api.get("/campaigns").then((r) => setRows(r.data));
  }, []);

  const filtered = rows.filter(
    (c) =>
      c.name?.toLowerCase().includes(q.toLowerCase()) ||
      c.campaign_type?.toLowerCase().includes(q.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-indigo-50 text-indigo-600 border border-indigo-100">
              <Megaphone className="w-5 h-5" />
            </div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Outreach Campaigns</h1>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Autonomous multi-touch calling workflows, sequence retry logic, and qualification.
          </p>
        </div>

        <Link className="btn btn-primary text-xs py-2 px-4 flex items-center gap-1.5" to="/app/campaigns/new">
          <Plus className="w-4 h-4" />
          <span>New Campaign</span>
        </Link>
      </div>

      {/* Overview Cards */}
      <div className="grid md:grid-cols-2 gap-4">
        <div className="card p-5 bg-white shadow-xs border-l-4 border-l-blue-500">
          <h2 className="font-bold text-slate-900 text-sm">Direct Voice Outreach</h2>
          <p className="text-xs text-slate-500 mt-1">Target existing filtered prospect lists with personalized voice qualification agents.</p>
        </div>
        <div className="card p-5 bg-white shadow-xs border-l-4 border-l-indigo-500">
          <h2 className="font-bold text-slate-900 text-sm">Signal Discovery & Outreach</h2>
          <p className="text-xs text-slate-500 mt-1">Continuous signal monitoring → automated enrichment → agent qualification sequence.</p>
        </div>
      </div>

      {/* Search Bar */}
      <div className="card p-3 bg-white shadow-xs">
        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            className="input search-input h-11 pr-10"
            placeholder="Search campaigns by title or type..."
            value={q}
            onChange={(e) => setQ(e.target.value)}
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
      </div>

      {/* Campaigns Table */}
      <div className="card overflow-hidden bg-white shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wider bg-slate-50/80 border-b border-slate-200">
              <tr>
                <th className="p-4">Campaign Name</th>
                <th className="p-4">Type</th>
                <th className="p-4">Status</th>
                <th className="p-4">Schedule / Region</th>
                <th className="p-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={5} className="p-8 text-center text-slate-400">
                    No campaigns found.
                  </td>
                </tr>
              ) : (
                filtered.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="p-4 font-semibold text-slate-900">
                      <Link className="hover:text-indigo-600 transition" to={`/app/campaigns/${c.id}`}>
                        {c.name}
                      </Link>
                    </td>
                    <td className="p-4 text-slate-600 text-xs">{c.campaign_type}</td>
                    <td className="p-4">
                      <span
                        className={`badge ${
                          c.status === "active" || c.status === "launched"
                            ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                            : "bg-slate-100 text-slate-600"
                        }`}
                      >
                        {c.status || "Ready"}
                      </span>
                    </td>
                    <td className="p-4 text-xs text-slate-500">
                      {c.schedule} · {c.timezone}
                    </td>
                    <td className="p-4 text-right">
                      <Link
                        to={`/app/campaigns/${c.id}`}
                        className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-600 hover:text-indigo-800"
                      >
                        <span>Console</span>
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
