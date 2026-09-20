import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

export default function Campaigns() {
  const [rows, setRows] = useState<any[]>([]);
  useEffect(() => {
    api.get("/campaigns").then((r) => setRows(r.data));
  }, []);
  return (
    <div>
      <div className="flex justify-between">
        <h1 className="text-2xl font-semibold">Campaigns</h1>
        <Link className="btn btn-primary" to="/app/campaigns/new">
          New campaign
        </Link>
      </div>
      <div className="grid md:grid-cols-2 gap-3 mt-4">
        <div className="card p-5">
          <h2 className="font-semibold">Option A — Calling only</h2>
          <p className="text-sm text-gray-600 mt-2">Existing leads → select agent → launch → qualification.</p>
        </div>
        <div className="card p-5">
          <h2 className="font-semibold">Option B — Leads + calling</h2>
          <p className="text-sm text-gray-600 mt-2">Discover → enrich → review → call → follow-up.</p>
        </div>
      </div>
      <table className="w-full text-sm card mt-6">
        <thead className="text-left text-gray-500">
          <tr>
            <th className="p-3">Name</th>
            <th>Type</th>
            <th>Status</th>
            <th>Schedule</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((c) => (
            <tr key={c.id} className="border-t border-gray-100">
              <td className="p-3">
                <Link className="text-blue-800" to={`/app/campaigns/${c.id}`}>
                  {c.name}
                </Link>
              </td>
              <td>{c.campaign_type}</td>
              <td>{c.status}</td>
              <td>
                {c.schedule} · {c.timezone}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
