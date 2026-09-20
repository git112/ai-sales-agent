import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

export default function Radar() {
  const [searches, setSearches] = useState<any[]>([]);
  const [notes, setNotes] = useState<any[]>([]);
  const [name, setName] = useState("SharePoint opportunities in India");
  const [query, setQuery] = useState("Companies looking for SharePoint implementation in India");
  const [frequency, setFrequency] = useState("daily");
  const [runMsg, setRunMsg] = useState("");

  async function load() {
    setSearches((await api.get("/saved-searches")).data);
    setNotes((await api.get("/notifications")).data);
  }
  useEffect(() => {
    load();
  }, []);
  return (
    <div>
      <h1 className="text-2xl font-semibold">Opportunity radar</h1>
      <p className="text-sm text-gray-500">Saved searches. Frequency is simulated — run now to generate DEMO notifications.</p>
      <div className="card p-4 mt-4 flex flex-wrap gap-2">
        <input className="input max-w-xs" value={name} onChange={(e) => setName(e.target.value)} />
        <input className="input" value={query} onChange={(e) => setQuery(e.target.value)} />
        <select className="input max-w-[120px]" value={frequency} onChange={(e) => setFrequency(e.target.value)}>
          <option value="daily">Daily</option>
          <option value="weekly">Weekly</option>
        </select>
        <button
          className="btn btn-primary"
          onClick={async () => {
            await api.post("/saved-searches", { name, query, frequency, source: "Demo Source", status: "active" });
            load();
          }}
        >
          Save search
        </button>
      </div>
      {searches.map((s) => (
        <div key={s.id} className="card p-4 mt-3 flex justify-between gap-3">
          <div>
            <div className="font-medium">{s.name}</div>
            <div className="text-sm text-gray-600">
              {s.query} · {s.frequency} · {s.status || "active"} · last run {s.last_run_at || "never"} · new matches {s.new_matches ?? 0}
            </div>
          </div>
          <div className="flex gap-2">
            <button
              className="btn btn-ghost"
              onClick={async () => {
                await api.patch(`/saved-searches/${s.id}`, { status: s.status === "paused" ? "active" : "paused" });
                load();
              }}
            >
              {s.status === "paused" ? "Activate" : "Pause"}
            </button>
            <button
              className="btn btn-ghost"
              onClick={async () => {
                const { data } = await api.post(`/saved-searches/${s.id}/run`);
                setRunMsg(`${data.new_matches ?? 0} new matches (DEMO DATA)`);
                load();
              }}
            >
              Run now
            </button>
          </div>
        </div>
      ))}
      {runMsg && <p className="text-sm mt-2">{runMsg}</p>}
      <h2 className="font-semibold mt-8">Notification inbox</h2>
      <Link className="text-sm text-blue-800" to="/app/notifications">
        View all notifications
      </Link>
      {notes.map((n) => (
        <div key={n.id} className="card p-4 mt-2">
          <div className="font-medium">{n.title}</div>
          <p className="text-sm text-gray-600">{n.body}</p>
          {n.why_matched && <p className="text-xs mt-1">Why matched: {n.why_matched}</p>}
          <p className="text-xs text-gray-500">
            Source {n.source || "Demo"} · Detected {n.detected_at || n.created_at}
          </p>
          {n.opportunity_id && (
            <Link className="text-sm text-blue-800" to={`/app/opportunities/${n.opportunity_id}`}>
              Open opportunity
            </Link>
          )}
          {!n.read && (
            <button className="btn btn-ghost ml-2" onClick={async () => { await api.post(`/notifications/${n.id}/read`); load(); }}>
              Mark as read
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
