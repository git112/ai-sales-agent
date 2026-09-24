import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Sparkles,
  Target,
  Flame,
  UserCheck,
  Megaphone,
  PhoneCall,
  CalendarCheck,
  Clock,
  ArrowUpRight,
  CheckCircle2
} from "lucide-react";
import { api } from "../api";

export default function Dashboard() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    api.get("/dashboard").then((r) => setData(r.data));
  }, []);

  if (!data) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="flex items-center gap-3 text-slate-500 text-sm">
          <div className="w-5 h-5 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
          <span>Loading sales intelligence…</span>
        </div>
      </div>
    );
  }

  const t = data.totals;

  const statCards = [
    { label: "Opportunities", value: t.opportunities, icon: Target, color: "text-indigo-600", bg: "bg-indigo-50" },
    { label: "High Intent", value: t.high_intent, icon: Flame, color: "text-amber-600", bg: "bg-amber-50" },
    { label: "Qualified", value: t.qualified_leads, icon: UserCheck, color: "text-emerald-600", bg: "bg-emerald-50" },
    { label: "Campaigns", value: t.active_campaigns, icon: Megaphone, color: "text-blue-600", bg: "bg-blue-50" },
    { label: "Calls", value: t.calls, icon: PhoneCall, color: "text-violet-600", bg: "bg-violet-50" },
    { label: "Meetings", value: t.meetings, icon: CalendarCheck, color: "text-teal-600", bg: "bg-teal-50" },
    { label: "Follow-ups", value: t.follow_ups, icon: Clock, color: "text-rose-600", bg: "bg-rose-50" },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Sales Intelligence Command</h1>
        <p className="text-sm text-slate-500 mt-1">Autonomous workspace telemetry and signal qualification metrics.</p>
      </div>

      {/* Modern KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
        {statCards.map((item) => {
          const Icon = item.icon;
          return (
            <div key={item.label} className="card p-4 bg-white hover:shadow-md transition-all">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">{item.label}</span>
                <div className={`p-1.5 rounded-lg ${item.bg} ${item.color}`}>
                  <Icon className="w-3.5 h-3.5" />
                </div>
              </div>
              <div className="text-2xl font-black text-slate-900 mt-2">{item.value}</div>
            </div>
          );
        })}
      </div>

      {/* Middle Grid: AI Insights & Next Actions */}
      <div className="grid md:grid-cols-2 gap-5">
        {/* AI Insights */}
        <div className="card p-5 bg-white shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-indigo-50 text-indigo-600">
                <Sparkles className="w-4 h-4" />
              </div>
              <h2 className="font-bold text-slate-900 text-base">AI Executive Insights</h2>
            </div>
            <span className="badge bg-indigo-50 text-indigo-700 border border-indigo-200/60">Real-Time</span>
          </div>
          <ul className="space-y-2.5">
            {data.insights.map((i: string, idx: number) => (
              <li
                key={idx}
                className="bg-slate-50 border border-slate-200/70 text-slate-700 rounded-xl px-3.5 py-2.5 text-sm flex items-start gap-2.5"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-600 mt-2 shrink-0"></span>
                <span>{i}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Next Actions */}
        <div className="card p-5 bg-white shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-emerald-50 text-emerald-600">
                <Clock className="w-4 h-4" />
              </div>
              <h2 className="font-bold text-slate-900 text-base">Prioritized Next Actions</h2>
            </div>
            <Link to="/app/tasks" className="text-xs font-semibold text-indigo-600 hover:text-indigo-800">
              View all
            </Link>
          </div>
          {data.next_actions.length === 0 ? (
            <p className="text-sm text-slate-400 py-6 text-center">No pending actions right now.</p>
          ) : (
            <div className="divide-y divide-slate-100">
              {data.next_actions.map((t: any) => (
                <Link
                  key={t.id}
                  to="/app/tasks"
                  className="py-3 flex items-center justify-between group hover:bg-slate-50 px-2 rounded-lg transition"
                >
                  <div className="min-w-0 pr-3">
                    <div className="text-sm font-semibold text-slate-800 group-hover:text-indigo-600 truncate transition">
                      {t.title}
                    </div>
                    <div className="text-xs text-slate-400 mt-0.5">Due: {t.due}</div>
                  </div>
                  <span
                    className={`badge text-[10px] shrink-0 ${
                      t.priority === "high"
                        ? "bg-rose-50 text-rose-700 border border-rose-200"
                        : "bg-slate-100 text-slate-600"
                    }`}
                  >
                    {t.priority}
                  </span>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Recent Opportunities */}
      <div className="card overflow-hidden bg-white shadow-xs">
        <div className="p-5 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h2 className="font-bold text-slate-900 text-base">Recent High-Value Opportunities</h2>
            <p className="text-xs text-slate-500 mt-0.5">Latest signals detected by autonomous radar</p>
          </div>
          <Link
            to="/app/opportunities"
            className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1"
          >
            <span>View All</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wider bg-slate-50/80 border-b border-slate-200">
              <tr>
                <th className="p-4">Company</th>
                <th className="p-4">Requirement</th>
                <th className="p-4">Score</th>
                <th className="p-4">Source</th>
                <th className="p-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.recent_opportunities.map((o: any) => (
                <tr key={o.id} className="hover:bg-slate-50/80 transition-colors">
                  <td className="p-4 font-semibold text-slate-900">
                    <Link className="hover:text-indigo-600 transition" to={`/app/opportunities/${o.id}`}>
                      {o.company_name || o.title}
                    </Link>
                  </td>
                  <td className="p-4 text-slate-600 max-w-md truncate">{o.requirement}</td>
                  <td className="p-4">
                    <span className="font-extrabold text-indigo-600">{o.score?.total ?? "—"}</span>
                  </td>
                  <td className="p-4 text-slate-500 text-xs">
                    <div className="flex items-center gap-1.5">
                      <span>{o.source}</span>
                      <span className="badge bg-emerald-50 text-emerald-700 border border-emerald-200/60 text-[10px]">
                        <CheckCircle2 className="w-2.5 h-2.5" />
                        Verified
                      </span>
                    </div>
                  </td>
                  <td className="p-4 text-right">
                    <Link
                      to={`/app/opportunities/${o.id}`}
                      className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-600 hover:text-indigo-800"
                    >
                      <span>Explore</span>
                      <ArrowUpRight className="w-3.5 h-3.5" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
