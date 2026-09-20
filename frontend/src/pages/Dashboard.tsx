import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

export default function Dashboard() {
  const [data, setData] = useState<any>(null);
  useEffect(() => {
    api.get("/dashboard").then((r) => setData(r.data));
  }, []);
  if (!data) return <p>Loading dashboard…</p>;
  const t = data.totals;
  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl">Sales intelligence</h1>
        <p className="text-gray-500 text-sm">Workspace metrics from JSON records — never invented.</p>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
        {[
          ["Opportunities", t.opportunities],
          ["High intent", t.high_intent],
          ["Qualified", t.qualified_leads],
          ["Campaigns", t.active_campaigns],
          ["Calls", t.calls],
          ["Meetings", t.meetings],
          ["Follow-ups", t.follow_ups],
        ].map(([k, v]) => (
          <div key={k} className="card p-4">
            <div className="text-xs text-gray-500">{k}</div>
            <div className="text-3xl font-display text-[#f0d089] mt-1">{v}</div>
          </div>
        ))}
      </div>
      <div className="grid md:grid-cols-2 gap-4">
        <div className="card p-5">
          <h2 className="font-semibold">AI insights</h2>
          <ul className="mt-3 space-y-2 text-sm text-gray-700">
            {data.insights.map((i: string) => (
              <li key={i} className="bg-blue-50 text-blue-900 rounded-lg px-3 py-2">
                {i}
              </li>
            ))}
          </ul>
        </div>
        <div className="card p-5">
          <h2 className="font-semibold">Next actions</h2>
          {data.next_actions.length === 0 && <p className="text-sm text-gray-500 mt-2">No open tasks yet.</p>}
          {data.next_actions.map((t: any) => (
            <Link key={t.id} to="/app/tasks" className="block text-sm py-2 border-b border-gray-100">
              {t.title} · {t.priority} · due {t.due}
            </Link>
          ))}
        </div>
      </div>
      <div className="card p-5">
        <h2 className="font-semibold mb-3">Recent opportunities</h2>
        <table className="w-full text-sm">
          <thead className="text-left text-gray-500">
            <tr>
              <th className="py-2">Company</th>
              <th>Requirement</th>
              <th>Score</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            {data.recent_opportunities.map((o: any) => (
              <tr key={o.id} className="border-t border-gray-100">
                <td className="py-2">
                  <Link className="text-blue-800" to={`/app/opportunities/${o.id}`}>
                    {o.company_name || o.title}
                  </Link>
                </td>
                <td>{o.requirement}</td>
                <td>{o.score?.total ?? "—"}</td>
                <td>
                  {o.source} <span className="badge bg-amber-50 text-amber-800 ml-2">DEMO DATA</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
