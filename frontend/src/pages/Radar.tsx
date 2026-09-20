import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

export default function Radar() {
  const [searches, setSearches] = useState<any[]>([]);
  const [notes, setNotes] = useState<any[]>([]);
  const [name, setName] = useState("SharePoint opportunities in India");
  const [query, setQuery] = useState("Companies looking for SharePoint implementation in India");
  useEffect(() => {
    api.get("/saved-searches").then((r) => setSearches(r.data));
    api.get("/notifications").then((r) => setNotes(r.data));
  }, []);
  return (
    <div>
      <h1 className="text-2xl font-semibold">Opportunity radar</h1>
      <p className="text-sm text-gray-500">Saved searches. Scheduling is simulated with DEMO DATA.</p>
      <div className="card p-4 mt-4 flex flex-wrap gap-2">
        <input className="input max-w-xs" value={name} onChange={(e) => setName(e.target.value)} />
        <input className="input" value={query} onChange={(e) => setQuery(e.target.value)} />
        <button
          className="btn btn-primary"
          onClick={async () => {
            await api.post("/saved-searches", { name, query, frequency: "daily", source: "Demo Source" });
            setSearches((await api.get("/saved-searches")).data);
          }}
        >
          Save search
        </button>
      </div>
      {searches.map((s) => (
        <div key={s.id} className="card p-4 mt-3 flex justify-between">
          <div>
            <div className="font-medium">{s.name}</div>
            <div className="text-sm text-gray-600">
              {s.query} · {s.frequency} · {s.status}
            </div>
          </div>
          <button
            className="btn btn-ghost"
            onClick={async () => {
              await api.post(`/saved-searches/${s.id}/run`);
              setNotes((await api.get("/notifications")).data);
            }}
          >
            Run now
          </button>
        </div>
      ))}
      <h2 className="font-semibold mt-8">Notifications</h2>
      {notes.map((n) => (
        <div key={n.id} className="card p-4 mt-2">
          <div className="font-medium">{n.title}</div>
          <p className="text-sm text-gray-600">{n.body}</p>
          {n.opportunity_id && (
            <Link className="text-sm text-blue-800" to={`/app/opportunities/${n.opportunity_id}`}>
              Open opportunity
            </Link>
          )}
        </div>
      ))}
    </div>
  );
}
