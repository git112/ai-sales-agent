import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { PhoneCall, Search, Clock, ArrowUpRight, X } from "lucide-react";
import { api } from "../api";

export default function Calls() {
  const [rows, setRows] = useState<any[]>([]);
  const [q, setQ] = useState("");

  useEffect(() => {
    api.get("/calls").then((r) => setRows(r.data));
  }, []);

  const filtered = rows.filter(
    (c) =>
      c.outcome?.toLowerCase().includes(q.toLowerCase()) ||
      c.label?.toLowerCase().includes(q.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-indigo-50 text-indigo-600 border border-indigo-100">
            <PhoneCall className="w-5 h-5" />
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Call History & Transcripts</h1>
        </div>
        <p className="text-sm text-slate-500 mt-1">
          Detailed conversational records, agent audio transcripts, interest qualification, and follow-up triggers.
        </p>
      </div>

      {/* Search Bar */}
      <div className="card p-3 bg-white shadow-xs">
        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            className="input search-input h-11 pr-10"
            placeholder="Filter calls by outcome or status..."
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

      {/* Calls Table */}
      <div className="card overflow-hidden bg-white shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wider bg-slate-50/80 border-b border-slate-200">
              <tr>
                <th className="p-4">Timestamp</th>
                <th className="p-4">Outcome</th>
                <th className="p-4">Context / Voicemail</th>
                <th className="p-4">Duration</th>
                <th className="p-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={5} className="p-8 text-center text-slate-400">
                    No calls recorded yet.
                  </td>
                </tr>
              ) : (
                filtered.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="p-4 font-semibold text-slate-900">
                      <Link className="hover:text-indigo-600 transition" to={`/app/calls/${c.id}`}>
                        {c.started_at}
                      </Link>
                    </td>
                    <td className="p-4">
                      <span
                        className={`badge ${
                          c.outcome === "Interested" || c.outcome === "Connected"
                            ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                            : c.outcome === "Callback Requested"
                            ? "bg-amber-50 text-amber-700 border border-amber-200"
                            : "bg-slate-100 text-slate-600"
                        }`}
                      >
                        {c.outcome}
                      </span>
                    </td>
                    <td className="p-4 text-slate-600 text-xs">
                      {c.label} {c.voicemail_message ? "· Voicemail Left" : ""}
                    </td>
                    <td className="p-4 text-slate-500 text-xs">{c.duration_sec}s</td>
                    <td className="p-4 text-right">
                      <Link
                        to={`/app/calls/${c.id}`}
                        className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-600 hover:text-indigo-800"
                      >
                        <span>Transcript</span>
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
