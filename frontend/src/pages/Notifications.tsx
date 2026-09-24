import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bell, CheckCheck, Check, ArrowUpRight, Flame, Sparkles, Filter } from "lucide-react";
import { api } from "../api";

export default function Notifications() {
  const [notes, setNotes] = useState<any[]>([]);
  const [filter, setFilter] = useState<"all" | "unread" | "high_intent">("all");
  const [loading, setLoading] = useState(true);

  async function load() {
    try {
      const { data } = await api.get("/notifications");
      setNotes(data);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const unreadCount = notes.filter((n) => !n.read).length;

  const filteredNotes = notes.filter((n) => {
    if (filter === "unread") return !n.read;
    if (filter === "high_intent") return n.title?.includes("HIGH INTENT") || n.body?.toLowerCase().includes("high intent");
    return true;
  });

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-indigo-50 text-indigo-600 border border-indigo-100">
              <Bell className="w-5 h-5" />
            </div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Notification Feed</h1>
            {unreadCount > 0 && (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-indigo-600 text-white">
                {unreadCount} unread
              </span>
            )}
          </div>
          <p className="text-sm text-slate-500 mt-1">Real-time alerts, high-intent discoveries, and qualification triggers.</p>
        </div>

        {unreadCount > 0 && (
          <button
            className="btn btn-ghost text-xs text-slate-600 hover:text-indigo-600 flex items-center gap-1.5"
            onClick={async () => {
              await api.post("/notifications/read-all");
              load();
            }}
          >
            <CheckCheck className="w-4 h-4 text-slate-500" />
            Mark all read
          </button>
        )}
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-200 pb-3">
        <Filter className="w-3.5 h-3.5 text-slate-400 mr-1" />
        {[
          { id: "all", label: `All (${notes.length})` },
          { id: "unread", label: `Unread (${unreadCount})` },
          { id: "high_intent", label: "High Intent" },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setFilter(tab.id as any)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              filter === tab.id
                ? "bg-indigo-600 text-white shadow-xs font-semibold"
                : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Notifications List */}
      {loading ? (
        <div className="p-12 text-center text-slate-400 text-sm">Loading notifications…</div>
      ) : filteredNotes.length === 0 ? (
        <div className="card p-12 text-center bg-white">
          <div className="w-12 h-12 rounded-2xl bg-slate-50 text-slate-400 mx-auto flex items-center justify-center mb-3">
            <Bell className="w-6 h-6" />
          </div>
          <h3 className="font-semibold text-slate-800">No notifications found</h3>
          <p className="text-sm text-slate-500 mt-1">
            {filter !== "all" ? "Try switching filter to All." : "Your alert feed is clear."}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredNotes.map((n) => {
            const isHighIntent = n.title?.includes("HIGH INTENT") || n.body?.toLowerCase().includes("high intent");
            return (
              <div
                key={n.id}
                className={`card p-5 bg-white transition-all hover:shadow-md relative overflow-hidden border-l-4 ${
                  isHighIntent
                    ? "border-l-amber-500"
                    : !n.read
                    ? "border-l-indigo-600"
                    : "border-l-slate-200"
                } ${n.read ? "opacity-75 bg-slate-50/40" : ""}`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-1.5 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      {isHighIntent ? (
                        <span className="badge bg-amber-50 text-amber-700 border border-amber-200/80">
                          <Flame className="w-3 h-3 text-amber-600" />
                          High Intent Prospect
                        </span>
                      ) : (
                        <span className="badge bg-indigo-50 text-indigo-700 border border-indigo-200/80">
                          <Sparkles className="w-3 h-3 text-indigo-600" />
                          Signal Match
                        </span>
                      )}
                      {!n.read && (
                        <span className="w-2 h-2 rounded-full bg-indigo-600" title="Unread"></span>
                      )}
                      <span className="text-xs text-slate-400">
                        {n.detected_at?.slice(0, 10) || n.created_at?.slice(0, 10) || "Recent"}
                      </span>
                    </div>

                    <h3 className="text-base font-semibold text-slate-900 leading-snug">{n.title}</h3>
                    <p className="text-sm text-slate-600 leading-relaxed">{n.body}</p>

                    {n.why_matched && (
                      <div className="text-xs text-slate-500 bg-slate-50 p-2 rounded-lg border border-slate-100 inline-block mt-1">
                        <span className="font-semibold text-slate-700">Trigger Match:</span> {n.why_matched}
                      </div>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="flex flex-col sm:flex-row items-end sm:items-center gap-2 shrink-0">
                    {n.opportunity_id && (
                      <Link
                        to={`/app/opportunities/${n.opportunity_id}`}
                        className="btn btn-primary text-xs py-1.5 px-3 flex items-center gap-1"
                      >
                        <span>Open Opportunity</span>
                        <ArrowUpRight className="w-3.5 h-3.5" />
                      </Link>
                    )}
                    {!n.read && (
                      <button
                        className="btn btn-ghost text-xs py-1.5 px-2.5 text-slate-500 hover:text-slate-800"
                        title="Mark as read"
                        onClick={async () => {
                          await api.post(`/notifications/${n.id}/read`);
                          load();
                        }}
                      >
                        <Check className="w-3.5 h-3.5" />
                        <span className="hidden sm:inline">Mark read</span>
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
