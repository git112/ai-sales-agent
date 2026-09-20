import { useEffect, useState } from "react";
import { api } from "../api";

export default function Tasks() {
  const [rows, setRows] = useState<any[]>([]);
  useEffect(() => {
    api.get("/tasks").then((r) => setRows(r.data));
  }, []);
  return (
    <div>
      <h1 className="text-2xl font-semibold">Follow-up tasks</h1>
      {rows.map((t) => (
        <div key={t.id} className="card p-4 mt-3 flex justify-between">
          <div>
            <div className="font-medium">{t.title}</div>
            <div className="text-sm text-gray-600">
              {t.priority} · due {t.due} · {t.status}
            </div>
            <div className="text-xs text-gray-500">{t.reason}</div>
          </div>
          <div className="flex gap-2">
            <button className="btn btn-ghost" onClick={() => api.patch(`/tasks/${t.id}`, { status: "complete" }).then(() => api.get("/tasks").then((r) => setRows(r.data)))}>
              Complete
            </button>
            <button
              className="btn btn-ghost"
              onClick={() => {
                const due = prompt("New due date YYYY-MM-DD", t.due);
                if (due) api.patch(`/tasks/${t.id}`, { due }).then(() => api.get("/tasks").then((r) => setRows(r.data)));
              }}
            >
              Reschedule
            </button>
            <button
              className="btn btn-ghost"
              onClick={() => {
                const who = prompt("Assignee", t.assignee || "");
                if (who != null) api.patch(`/tasks/${t.id}`, { assignee: who }).then(() => api.get("/tasks").then((r) => setRows(r.data)));
              }}
            >
              Assign
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
