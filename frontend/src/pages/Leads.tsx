import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

const stages = ["discovered", "reviewed", "contacted", "qualified", "meeting", "proposal", "won", "lost"];

export default function Leads() {
  const [rows, setRows] = useState<any[]>([]);
  const [q, setQ] = useState("");
  const [stage, setStage] = useState("");
  const [pipe, setPipe] = useState<any>({});

  async function load() {
    const params: any = {};
    if (q) params.q = q;
    if (stage) params.stage = stage;
    const { data } = await api.get("/leads", { params });
    setRows(data);
    setPipe((await api.get("/leads/pipeline")).data);
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
    <div>
      <div className="flex justify-between">
        <h1 className="text-2xl font-semibold">Leads</h1>
        <div className="flex gap-2">
          <Link className="btn btn-ghost" to="/app/leads/import">
            Import CSV / Excel
          </Link>
          <Link className="btn btn-ghost" to="/app/leads/segments">
            Segments
          </Link>
          <button className="btn btn-ghost" onClick={() => download("csv")}>
            Export CSV
          </button>
          <button className="btn btn-ghost" onClick={() => download("xlsx")}>
            Export Excel
          </button>
        </div>
      </div>
      <div className="flex gap-2 mt-4">
        <input className="input" placeholder="Search" value={q} onChange={(e) => setQ(e.target.value)} />
        <select className="input max-w-xs" value={stage} onChange={(e) => setStage(e.target.value)}>
          <option value="">All stages</option>
          {stages.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
        <button className="btn btn-primary" onClick={load}>
          Filter
        </button>
      </div>
      <div className="flex gap-2 overflow-x-auto mt-4 pb-2">
        {stages.map((s) => (
          <div key={s} className="card p-3 min-w-[140px]">
            <div className="text-xs text-gray-500 uppercase">{s}</div>
            <div className="text-xl font-semibold">{(pipe[s] || []).length}</div>
          </div>
        ))}
      </div>
      <table className="w-full text-sm mt-4 card">
        <thead className="text-left text-gray-500">
          <tr>
            <th className="p-3">Company</th>
            <th>Contact</th>
            <th>Stage</th>
            <th>Score</th>
            <th>Intent</th>
            <th>Source</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((l) => (
            <tr key={l.id} className="border-t border-gray-100">
              <td className="p-3">
                <Link className="text-blue-800" to={`/app/leads/${l.id}`}>
                  {l.company}
                </Link>
                <span className="badge bg-amber-50 text-amber-800 ml-2">DEMO</span>
              </td>
              <td>{l.name || "—"}</td>
              <td>{l.pipeline_stage}</td>
              <td>{l.opportunity_score ?? "—"}</td>
              <td>{l.intent_level}</td>
              <td>{l.source}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
