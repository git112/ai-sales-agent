import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";

const OUTCOMES = ["Connected", "No Answer", "Voicemail", "Callback Requested", "Not Interested", "Interested", "Escalated"];

export default function CampaignDetail() {
  const { id } = useParams();
  const [camp, setCamp] = useState<any>(null);
  const [result, setResult] = useState<any>(null);
  const [hint, setHint] = useState("Interested");
  const [busy, setBusy] = useState("");
  const [err, setErr] = useState("");
  useEffect(() => {
    api.get(`/campaigns/${id}`).then((r) => setCamp(r.data));
  }, [id]);
  if (!camp) return <p>Loading…</p>;
  const leadId = camp.lead_ids?.[0] || "lead_abc";
  const timeline = camp.timeline || [];
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">{camp.name}</h1>
      <span className="badge bg-amber-50 text-amber-800">DEMO CAMPAIGN SIMULATION</span>
      <p className="text-sm text-gray-600">
        {camp.campaign_type} · {camp.status} · {camp.schedule} · {camp.timezone} · quiet {camp.quiet_hours?.start}-{camp.quiet_hours?.end}
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
          {OUTCOMES.map((h) => (
            <option key={h}>{h}</option>
          ))}
        </select>
        <button
          className="btn btn-primary mt-3 ml-2"
          disabled={busy === "sim"}
          onClick={async () => {
            setBusy("sim");
            setErr("");
            try {
              const { data } = await api.post(`/campaigns/${id}/calls/simulate`, { lead_id: leadId, outcome_hint: hint });
              setResult(data);
            } catch (e: any) {
              setErr(e.response?.data?.error?.message || "Simulation failed");
            } finally {
              setBusy("");
            }
          }}
        >
          {busy === "sim" ? "Running…" : "Simulate call"}
        </button>
        <button
          className="btn btn-ghost mt-3 ml-2"
          disabled={busy === "step"}
          onClick={async () => {
            setBusy("step");
            setErr("");
            try {
              const { data } = await api.post(`/campaigns/${id}/next-step`, {}, { params: { lead_id: leadId, force: true } });
              setResult(data.result || data);
              setCamp(data.campaign || camp);
            } catch (e: any) {
              setErr(e.response?.data?.error?.message || "Step failed");
            } finally {
              setBusy("");
            }
          }}
        >
          {busy === "step" ? "Stepping…" : "Run next campaign step"}
        </button>
        {err && <p className="text-sm text-red-600 mt-2">{err}</p>}
      </div>
      <div className="card p-5">
        <h2 className="font-semibold">Campaign timeline</h2>
        {timeline.length === 0 && <p className="text-sm text-gray-500 mt-2">No simulated attempts yet.</p>}
        {timeline.map((t: any, i: number) => (
          <div key={i} className="text-sm py-2 border-b" style={{ borderColor: "var(--line)" }}>
            Attempt {t.attempt} → {t.outcome}
            {t.retry_scheduled ? " → Retry scheduled" : ""}
            {t.outcome === "Interested" ? " → Qualified → HIGH INTENT" : ""}
          </div>
        ))}
      </div>
      {result && (
        <div className="card p-5 space-y-2">
          <span className="badge bg-amber-50 text-amber-800">{result.label}</span>
          {result.call?.retry_eligible && <p className="text-sm">Retry eligible (No Answer / Voicemail).</p>}
          {result.qualification?.high_intent && <div className="text-red-700 font-semibold">HIGH INTENT PROSPECT</div>}
          <p className="text-sm">{result.transcript?.summary || result.call?.outcome}</p>
          <p className="text-sm">
            Next best action: <strong>{result.next_best_action?.action}</strong>
          </p>
          {result.task && (
            <p className="text-sm">
              Task created: {result.task.title} due {result.task.due}
            </p>
          )}
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
