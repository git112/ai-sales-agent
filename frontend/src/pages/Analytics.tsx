import { useEffect, useState } from "react";
import { BarChart3, PhoneCall, CheckCircle2, UserCheck, Flame, Clock, TrendingUp, Sparkles } from "lucide-react";
import { api } from "../api";

export default function Analytics() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    api.get("/analytics/calls").then((r) => setData(r.data));
  }, []);

  if (!data) {
    return (
      <div className="flex items-center justify-center min-h-[300px] text-slate-500 text-sm">
        <div className="flex items-center gap-2.5">
          <div className="w-4 h-4 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
          <span>Loading analytics engine…</span>
        </div>
      </div>
    );
  }

  const k = data.kpis || {};

  const kpiItems = [
    { label: "Calls Attempted", value: k.calls_attempted ?? 0, icon: PhoneCall, color: "text-indigo-600", bg: "bg-indigo-50" },
    { label: "Connected", value: k.connected ?? 0, icon: CheckCircle2, color: "text-emerald-600", bg: "bg-emerald-50" },
    { label: "Voicemail", value: k.voicemail ?? 0, icon: Clock, color: "text-slate-600", bg: "bg-slate-100" },
    { label: "Qualification %", value: `${k.qualification_rate ?? 0}%`, icon: Sparkles, color: "text-violet-600", bg: "bg-violet-50" },
    { label: "High Interest", value: k.interested ?? 0, icon: Flame, color: "text-amber-600", bg: "bg-amber-50" },
    { label: "Callbacks", value: k.callbacks ?? 0, icon: TrendingUp, color: "text-blue-600", bg: "bg-blue-50" },
    { label: "Opt-outs", value: k.opt_outs ?? 0, icon: UserCheck, color: "text-rose-600", bg: "bg-rose-50" },
    { label: "Avg Duration", value: `${k.avg_duration_sec ?? 0}s`, icon: Clock, color: "text-teal-600", bg: "bg-teal-50" },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-indigo-50 text-indigo-600 border border-indigo-100">
            <BarChart3 className="w-5 h-5" />
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Call & Outreach Analytics</h1>
        </div>
        <p className="text-sm text-slate-500 mt-1">
          Performance metrics, conversation qualification yield, and campaign delivery telemetry.
        </p>
      </div>

      {/* KPI Stat Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-4 gap-3">
        {kpiItems.map((item) => {
          const Icon = item.icon;
          return (
            <div key={item.label} className="card p-4 bg-white shadow-xs hover:shadow-sm transition-all">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">{item.label}</span>
                <div className={`p-1.5 rounded-lg ${item.bg} ${item.color}`}>
                  <Icon className="w-3.5 h-3.5" />
                </div>
              </div>
              <div className="text-2xl font-black text-slate-900 mt-2 font-display">{item.value}</div>
            </div>
          );
        })}
      </div>

      {/* Analytics Charts Grid */}
      <div className="grid md:grid-cols-2 gap-4">
        <Chart title="Calls Over Time" items={(data.calls_over_time || []).map((s: any) => ({ label: s.date, n: s.calls }))} />
        <Chart title="Lead Sources" items={(data.lead_sources || []).map((s: any) => ({ label: s.source, n: s.count }))} />
        <Chart title="Qualification Outcomes" items={(data.qualification_outcomes || []).map((s: any) => ({ label: s.outcome, n: s.count }))} />
        <div className="card p-5 bg-white shadow-xs space-y-3">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
            <h2 className="font-bold text-slate-900 text-sm">Campaign Performance</h2>
            <span className="badge bg-indigo-50 text-indigo-700 border border-indigo-200">Active</span>
          </div>
          {(data.campaign_performance || []).length === 0 ? (
            <p className="text-xs text-slate-400 py-2">No campaign execution runs yet.</p>
          ) : (
            <div className="divide-y divide-slate-100">
              {(data.campaign_performance || []).map((c: any) => (
                <div key={c.name} className="flex items-center justify-between py-2.5 text-xs">
                  <div>
                    <span className="font-semibold text-slate-800">{c.name}</span>
                    <span className="ml-2 px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 font-medium capitalize">{c.status}</span>
                  </div>
                  <span className="font-semibold text-indigo-600">{c.leads} leads</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Chart({ title, items }: { title: string; items: { label: string; n: number }[] }) {
  const max = Math.max(1, ...items.map((i) => i.n));
  return (
    <div className="card p-5 bg-white shadow-xs space-y-3">
      <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
        <h2 className="font-bold text-slate-900 text-sm">{title}</h2>
        <span className="text-[11px] text-slate-400 font-medium">{items.length} records</span>
      </div>
      {items.length === 0 ? (
        <p className="text-xs text-slate-400 py-3">No activity logged in this reporting window.</p>
      ) : (
        <div className="space-y-3">
          {items.map((i) => (
            <div key={i.label} className="space-y-1">
              <div className="flex justify-between text-xs font-medium text-slate-700">
                <span className="truncate pr-2">{i.label}</span>
                <span className="font-bold text-slate-900">{i.n}</span>
              </div>
              <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-indigo-500 to-indigo-600 rounded-full transition-all duration-300"
                  style={{ width: `${Math.min(100, Math.max(4, (i.n / max) * 100))}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
