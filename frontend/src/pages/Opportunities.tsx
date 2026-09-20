import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

export default function Opportunities() {
  const [q, setQ] = useState("Find companies looking for SharePoint implementation.");
  const [rows, setRows] = useState<any[]>([]);
  const [note, setNote] = useState("");
  const [sources, setSources] = useState<any[]>([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function load() {
    const { data } = await api.get("/opportunities");
    setRows(data);
  }
  useEffect(() => {
    load();
  }, []);

  async function search() {
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

  return (
    <div>
      <h1 className="font-display text-3xl">Find opportunities</h1>
      <p className="text-sm text-gray-500 mt-1">Natural language search against permitted demo sources. Results are labeled DEMO DATA.</p>
      <div className="flex gap-2 mt-4">
        <input className="input" value={q} onChange={(e) => setQ(e.target.value)} />
        <button className="btn btn-primary" disabled={busy} onClick={search}>
          {busy ? "Searching…" : "Find opportunities"}
        </button>
      </div>
      {err && <p className="text-sm text-red-600 mt-2">{err}</p>}
      {note && <p className="text-xs text-amber-800 mt-2">{note}</p>}
      {sources.length > 0 && (
        <div className="grid md:grid-cols-2 gap-2 mt-3">
          {sources.map((s) => (
            <div key={s.name} className="card p-3 text-xs">
              <div className="font-medium">{s.name}</div>
              <div>Last fetched: {s.last_fetched_at || "—"}</div>
              <div>Discovered: {s.discovered ?? "—"}</div>
              <div className="text-amber-800">{s.error || s.fallback || "OK"}</div>
            </div>
          ))}
        </div>
      )}
      <div className="mt-6 space-y-3">
        {rows.filter((o) => String(o.id || "").startsWith("opp_")).map((o) => (
          <Link key={o.id} to={`/app/opportunities/${o.id}`} className="card p-5 block tilt-3d">
            <div className="flex justify-between">
              <div>
                <div className="font-semibold">{o.company_name || o.title || o.requirement}</div>
                <div className="text-sm text-gray-600 mt-1">{o.requirement || o.description}</div>
                <div className="text-xs text-gray-500 mt-2">
                  SOURCE {o.source} · URL {o.original_url || o.source_url || "Not detected"} · DETECTED {o.detected_at?.slice(0, 10) || o.published_at?.slice(0, 10) || "Not detected"} · CONFIDENCE {o.confidence ?? "Not detected"}
                </div>
              </div>
              <div className="text-right">
                <div className="text-3xl font-display text-[#f0d089]">{o.score?.total ?? "—"}</div>
                <div className="text-xs text-gray-500">AI Opportunity Score</div>
                <span className="badge bg-amber-50 text-amber-800 mt-2">{o.label || "DEMO DATA"}</span>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
