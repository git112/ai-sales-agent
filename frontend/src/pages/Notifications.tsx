import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

export default function Notifications() {
  const [notes, setNotes] = useState<any[]>([]);
  async function load() {
    setNotes((await api.get("/notifications")).data);
  }
  useEffect(() => {
    load();
  }, []);
  return (
    <div>
      <div className="flex justify-between">
        <h1 className="text-2xl font-semibold">Notifications</h1>
        <button className="btn btn-ghost" onClick={async () => { await api.post("/notifications/read-all"); load(); }}>
          Mark all read
        </button>
      </div>
      {notes.length === 0 && <p className="text-sm text-gray-500 mt-4">No notifications yet. Run a saved search on Radar.</p>}
      {notes.map((n) => (
        <div key={n.id} className={`card p-4 mt-3 ${n.read ? "opacity-70" : ""}`}>
          <div className="font-medium">{n.title}</div>
          <p className="text-sm text-gray-600">{n.body}</p>
          {n.opportunity_id && (
            <Link className="text-sm text-blue-800" to={`/app/opportunities/${n.opportunity_id}`}>
              Open opportunity
            </Link>
          )}
          {!n.read && (
            <button className="btn btn-ghost" onClick={async () => { await api.post(`/notifications/${n.id}/read`); load(); }}>
              Mark as read
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
