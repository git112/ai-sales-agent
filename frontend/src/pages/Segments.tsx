import { useEffect, useState } from "react";
import { api } from "../api";

export default function Segments() {
  const [rows, setRows] = useState<any[]>([]);
  const [name, setName] = useState("High-intent SharePoint leads in India");
  const [minScore, setMinScore] = useState(80);
  const [location, setLocation] = useState("India");
  useEffect(() => {
    api.get("/segments").then((r) => setRows(r.data));
  }, []);
  return (
    <div>
      <h1 className="text-2xl font-semibold">Lead segments</h1>
      <div className="card p-4 mt-4 flex flex-wrap gap-2 items-end">
        <input className="input max-w-sm" value={name} onChange={(e) => setName(e.target.value)} />
        <input className="input max-w-[140px]" type="number" value={minScore} onChange={(e) => setMinScore(+e.target.value)} />
        <input className="input max-w-[160px]" value={location} onChange={(e) => setLocation(e.target.value)} />
        <button
          className="btn btn-primary"
          onClick={async () => {
            await api.post("/segments", { name, type: "dynamic", filters: { min_score: minScore, location_contains: location } });
            setRows((await api.get("/segments")).data);
          }}
        >
          Save dynamic segment
        </button>
      </div>
      {rows.map((s) => (
        <div key={s.id || s.name} className="card p-4 mt-3">
          <div className="font-medium">
            {s.name} · {s.type} · {s.count} leads
          </div>
          <div className="text-sm text-gray-600">{(s.leads || []).map((l: any) => l.company).join(", ")}</div>
        </div>
      ))}
    </div>
  );
}
