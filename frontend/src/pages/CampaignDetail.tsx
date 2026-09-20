import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";

export default function CampaignDetail() {
  const { id } = useParams();
  const [camp, setCamp] = useState<any>(null);
  const [result, setResult] = useState<any>(null);
  const [hint, setHint] = useState("Interested");
  useEffect(() => {
    api.get(`/campaigns/${id}`).then((r) => setCamp(r.data));
  }, [id]);
  if (!camp) return <p>Loading…</p>;
  const leadId = camp.lead_ids?.[0] || "lead_abc";
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">{camp.name}</h1>
      <p className="text-sm text-gray-600">
        {camp.campaign_type} · {camp.status} · {camp.schedule} · {camp.timezone}
      </p>
      <div className="flex gap-2">
        <button className="btn btn-primary" onClick={() => api.post(`/campaigns/${id}/launch`).then((r) => setCamp(r.data))}>
          Launch
        </button>
        <button className="btn btn-ghost" onClick={() => api.post(`/campaigns/${id}/pause`).then((r) => setCamp(r.data))}>
          Pause
        </button>
        <button className="btn btn-ghost" onClick={() => api.post(`/campaigns/${id}/resume`).then((r) => setCamp(r.data))}>
          Resume
        </button>
      </div>
      <div className="card p-5">
        <h2 className="font-semibold">Demo Voice Simulation</h2>
        <p className="text-sm text-gray-600">Never claimed as a live call. Choose a simulated outcome, then run.</p>
        <select className="input max-w-xs mt-3" value={hint} onChange={(e) => setHint(e.target.value)}>
          {["Interested", "Voicemail", "Callback Requested", "Not Interested"].map((h) => (
            <option key={h}>{h}</option>
          ))}
        </select>
        <button
          className="btn btn-primary mt-3 ml-2"
          onClick={async () => {
            const { data } = await api.post(`/campaigns/${id}/calls/simulate`, {
              lead_id: leadId,
              outcome_hint: hint,
              prospect_script:
                hint === "Interested"
                  ? "We are looking for SharePoint migration support and want to start this month."
                  : undefined,
            });
            setResult(data);
          }}
        >
          Simulate call
        </button>
      </div>
      {result && (
        <div className="card p-5 space-y-2">
          <span className="badge bg-amber-50 text-amber-800">{result.label}</span>
          {result.qualification?.high_intent && <div className="text-red-700 font-semibold">HIGH INTENT PROSPECT</div>}
          <p className="text-sm">{result.transcript?.summary}</p>
          <p className="text-sm">
            Next best action: <strong>{result.next_best_action?.action}</strong>
          </p>
          {result.task && <p className="text-sm">Task created: {result.task.title} due {result.task.due}</p>}
          {result.call && (
            <Link className="text-blue-800 text-sm" to={`/app/calls/${result.call.id}`}>
              Open transcript
            </Link>
          )}
        </div>
      )}
    </div>
  );
}
