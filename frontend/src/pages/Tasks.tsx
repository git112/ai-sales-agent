import { useEffect, useState } from "react";
import { CheckSquare, Calendar, User, CheckCircle2, Clock, X, AlertCircle } from "lucide-react";
import { api } from "../api";

export default function Tasks() {
  const [rows, setRows] = useState<any[]>([]);
  const [filter, setFilter] = useState<"all" | "pending" | "complete">("all");
  const [editingTask, setEditingTask] = useState<any>(null);
  const [editDue, setEditDue] = useState("");
  const [editAssignee, setEditAssignee] = useState("");
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const { data } = await api.get("/tasks");
      setRows(data);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function updateStatus(id: string, status: string) {
    await api.patch(`/tasks/${id}`, { status });
    load();
  }

  async function saveEdit() {
    if (!editingTask) return;
    await api.patch(`/tasks/${editingTask.id}`, {
      due: editDue || editingTask.due,
      assignee: editAssignee
    });
    setEditingTask(null);
    load();
  }

  const filteredTasks = rows.filter((t) => {
    if (filter === "pending") return t.status !== "complete";
    if (filter === "complete") return t.status === "complete";
    return true;
  });

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-indigo-50 text-indigo-600 border border-indigo-100">
              <CheckSquare className="w-5 h-5" />
            </div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Follow-up Tasks & Actions</h1>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Autonomous follow-up queue generated from qualifying calls and prospect interest signals.
          </p>
        </div>

        {/* Filter Tabs */}
        <div className="flex items-center gap-1.5 bg-slate-100 p-1 rounded-xl">
          {[
            { id: "all", label: "All" },
            { id: "pending", label: "Pending" },
            { id: "complete", label: "Completed" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setFilter(tab.id as any)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                filter === tab.id
                  ? "bg-white text-slate-900 shadow-xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Task List */}
      <div className="space-y-3">
        {filteredTasks.length === 0 ? (
          <div className="card p-12 text-center bg-white">
            <CheckCircle2 className="w-10 h-10 text-slate-300 mx-auto mb-2" />
            <p className="text-sm text-slate-500">No tasks in this view.</p>
          </div>
        ) : (
          filteredTasks.map((t) => (
            <div
              key={t.id}
              className={`card p-5 bg-white transition-all hover:shadow-md flex flex-col sm:flex-row sm:items-center justify-between gap-4 ${
                t.status === "complete" ? "opacity-60 bg-slate-50/50" : ""
              }`}
            >
              <div className="space-y-1.5 flex-1">
                <div className="flex items-center gap-2">
                  <span
                    className={`font-semibold text-base ${
                      t.status === "complete" ? "line-through text-slate-500" : "text-slate-900"
                    }`}
                  >
                    {t.title}
                  </span>
                  <span
                    className={`badge text-[10px] ${
                      t.priority === "high"
                        ? "bg-rose-50 text-rose-700 border border-rose-200"
                        : t.priority === "medium"
                        ? "bg-amber-50 text-amber-700 border border-amber-200"
                        : "bg-slate-100 text-slate-600"
                    }`}
                  >
                    {t.priority}
                  </span>
                  <span
                    className={`badge text-[10px] ${
                      t.status === "complete"
                        ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                        : "bg-blue-50 text-blue-700 border border-blue-200"
                    }`}
                  >
                    {t.status}
                  </span>
                </div>

                <div className="flex items-center gap-4 text-xs text-slate-500 flex-wrap">
                  <div className="flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5 text-slate-400" />
                    <span>Due: {t.due}</span>
                  </div>
                  {t.assignee && (
                    <div className="flex items-center gap-1">
                      <User className="w-3.5 h-3.5 text-slate-400" />
                      <span>Assigned: {t.assignee}</span>
                    </div>
                  )}
                </div>

                {t.reason && <div className="text-xs text-slate-500 italic">“{t.reason}”</div>}
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2 shrink-0">
                {t.status !== "complete" ? (
                  <button
                    className="btn btn-ghost text-xs py-1.5 px-3 text-emerald-700 hover:bg-emerald-50 hover:border-emerald-200"
                    onClick={() => updateStatus(t.id, "complete")}
                  >
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                    <span>Done</span>
                  </button>
                ) : (
                  <button
                    className="btn btn-ghost text-xs py-1.5 px-3 text-slate-500"
                    onClick={() => updateStatus(t.id, "open")}
                  >
                    <span>Reopen</span>
                  </button>
                )}

                <button
                  className="btn btn-ghost text-xs py-1.5 px-3"
                  onClick={() => {
                    setEditingTask(t);
                    setEditDue(t.due || "");
                    setEditAssignee(t.assignee || "");
                  }}
                >
                  <span>Edit / Assign</span>
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Proper UI Edit Modal (Replacing prompt) */}
      {editingTask && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="card p-6 bg-white max-w-md w-full shadow-lg space-y-4 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="font-bold text-slate-900 text-base">Update Task Details</h3>
              <button
                onClick={() => setEditingTask(null)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="text-xs text-slate-500 font-medium">{editingTask.title}</div>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Due Date</label>
                <input
                  type="date"
                  className="input h-10"
                  value={editDue}
                  onChange={(e) => setEditDue(e.target.value)}
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Assignee</label>
                <input
                  type="text"
                  className="input h-10"
                  placeholder="e.g. Sarah Connor or sarah@example.com"
                  value={editAssignee}
                  onChange={(e) => setEditAssignee(e.target.value)}
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
              <button className="btn btn-ghost text-xs" onClick={() => setEditingTask(null)}>
                Cancel
              </button>
              <button className="btn btn-primary text-xs" onClick={saveEdit}>
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
