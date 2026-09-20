import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

export default function Opportunities() {
  const [q, setQ] = useState("Find companies looking for SharePoint implementation.");
  const [rows, setRows] = useState<any[]>([]);
  const [note, setNote] = useState("");

  async function load() {
    const { data } = await api.get("/opportunities");
    setRows(data);
  }
  useEffect(() => {
    load();
  }, []);

  async function search() {
    const { data } = await api.post("/opportunities/search", { query: q });
    setNote(data.source_note);
    setRows(data.results);
  }

  return (
    <div>
      <h1 className="font-display text-3xl">Find opportunities</h1>
      <p className="text-sm text-gray-500 mt-1">Natural language search against permitted demo sources. Results are labeled DEMO DATA.</p>
      <div className="flex gap-2 mt-4">
        <input className="input" value={q} onChange={(e) => setQ(e.target.value)} />
        <button className="btn btn-primary" onClick={search}>
          Find opportunities
        </button>
      </div>
      {note && <p className="text-xs text-amber-800 mt-2">{note}</p>}
      <div className="mt-6 space-y-3">
        {rows.filter((o) => String(o.id || "").startsWith("opp_")).map((o) => (
          <Link key={o.id} to={`/app/opportunities/${o.id}`} className="card p-5 block tilt-3d">
            <div className="flex justify-between">
              <div>
                <div className="font-semibold">{o.company_name || o.title || o.requirement}</div>
                <div className="text-sm text-gray-600 mt-1">{o.requirement || o.description}</div>
                <div className="text-xs text-gray-500 mt-2">
                  {o.location} · {o.source} · {o.published_at?.slice(0, 10)}
                </div>
              </div>
              <div className="text-right">
                <div className="text-3xl font-display text-[#f0d089]">{o.score?.total ?? "—"}</div>
                <div className="text-xs text-gray-500">AI Opportunity Score</div>
                <span className="badge bg-amber-50 text-amber-800 mt-2">DEMO DATA</span>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
