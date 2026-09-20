import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

export default function Calls() {
  const [rows, setRows] = useState<any[]>([]);
  useEffect(() => {
    api.get("/calls").then((r) => setRows(r.data));
  }, []);
  return (
    <div>
      <h1 className="text-2xl font-semibold">Calls</h1>
      <table className="w-full text-sm card mt-4">
        <thead className="text-left text-gray-500">
          <tr>
            <th className="p-3">When</th>
            <th>Outcome</th>
            <th>Mode</th>
            <th>Duration</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((c) => (
            <tr key={c.id} className="border-t border-gray-100">
              <td className="p-3">
                <Link className="text-blue-800" to={`/app/calls/${c.id}`}>
                  {c.started_at}
                </Link>
              </td>
              <td>{c.outcome}</td>
              <td>
                {c.label} {c.voicemail_message ? "· Voicemail" : ""}
              </td>
              <td>{c.duration_sec}s</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
