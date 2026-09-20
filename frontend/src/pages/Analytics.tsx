import { useEffect, useState } from "react";
import { api } from "../api";

export default function Analytics() {
  const [data, setData] = useState<any>(null);
  useEffect(() => {
    api.get("/analytics/calls").then((r) => setData(r.data));
  }, []);
  if (!data) return <p>Loading…</p>;
  const k = data.kpis || {};
  return (
    <div>
      <h1 className="text-2xl font-semibold">Call analytics</h1>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
        {[
          ["Attempted", k.calls_attempted],
          ["Connected", k.connected],
          ["Voicemail", k.voicemail],
          ["Qualification %", k.qualification_rate],
          ["Interested", k.interested],
          ["Callbacks", k.callbacks],
          ["Opt-outs", k.opt_outs],
          ["Avg duration", k.avg_duration_sec],
        ].map(([l, v]) => (
          <div key={l} className="card p-4">
            <div className="text-xs text-gray-500">{l}</div>
            <div className="text-xl font-semibold">{v ?? 0}</div>
          </div>
        ))}
      </div>
      <div className="grid md:grid-cols-2 gap-4 mt-4">
        <Chart title="Calls over time" items={(data.calls_over_time || []).map((s: any) => ({ label: s.date, n: s.calls }))} />
        <Chart title="Lead sources" items={(data.lead_sources || []).map((s: any) => ({ label: s.source, n: s.count }))} />
        <Chart title="Qualification outcomes" items={(data.qualification_outcomes || []).map((s: any) => ({ label: s.outcome, n: s.count }))} />
        <div className="card p-4">
          <h2 className="font-semibold text-sm">Campaign performance</h2>
          {(data.campaign_performance || []).map((c: any) => (
            <div key={c.name} className="text-sm py-1">
              {c.name} · {c.status} · {c.leads} leads
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Chart({ title, items }: { title: string; items: { label: string; n: number }[] }) {
  const max = Math.max(1, ...items.map((i) => i.n));
  return (
    <div className="card p-4">
      <h2 className="font-semibold text-sm">{title}</h2>
      {items.length === 0 && <p className="text-xs text-gray-500 mt-2">No data yet.</p>}
      {items.map((i) => (
        <div key={i.label} className="mt-2">
          <div className="flex justify-between text-xs">
            <span>{i.label}</span>
            <span>{i.n}</span>
          </div>
          <div className="h-2 bg-gray-100 rounded">
            <div className="h-2 bg-blue-600 rounded" style={{ width: `${(i.n / max) * 100}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}
