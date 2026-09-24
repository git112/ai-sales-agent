import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api";

export default function CallDetail() {
  const { id } = useParams();
  const [data, setData] = useState<any>(null);
  useEffect(() => {
    api.get(`/calls/${id}`).then((r) => setData(r.data));
  }, [id]);
  if (!data) return <p>Loading…</p>;
  const { call, transcript, qualification } = data;
  return (
    <div className="space-y-5 max-w-3xl">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold text-slate-900">Call Outcome: {call.outcome}</h1>
            <span className="badge bg-indigo-50 text-indigo-700 border border-indigo-200">
              {call.outcome}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">Duration: {call.duration_sec}s · Started: {call.started_at}</p>
        </div>
      </div>

      {call.voicemail_message && (
        <div className="card p-4 bg-white shadow-xs">
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Approved Voicemail Message</div>
          <p className="text-sm mt-1 text-slate-700">{call.voicemail_message}</p>
        </div>
      )}

      {call.retry_eligible && (
        <div className="text-xs font-semibold text-amber-700 bg-amber-50 px-3 py-1.5 rounded-lg border border-amber-200 inline-block">
          Sequence Active: Scheduled for retry attempt
        </div>
      )}

      {call.escalated && (
        <div className="text-xs font-semibold text-indigo-700 bg-indigo-50 px-3 py-1.5 rounded-lg border border-indigo-200">
          Escalated Handoff: {call.handoff_reason} · {call.escalated_at}
        </div>
      )}

      {qualification?.high_intent && (
        <div className="badge bg-amber-50 text-amber-800 border border-amber-200">
          HIGH INTENT PROSPECT DETECTED
        </div>
      )}
      <div className="card p-4">
        <h2 className="font-semibold">Summary</h2>
        <p className="text-sm mt-2">{transcript?.summary}</p>
        <p className="text-sm mt-2">Requirements: {transcript?.requirements || "—"}</p>
        <p className="text-sm">Interest: {transcript?.interest_level}</p>
        <p className="text-sm">Recommended: {transcript?.recommended_action?.action}</p>
      </div>
      <div className="card p-4">
        <h2 className="font-semibold">Transcript</h2>
        {(transcript?.turns || []).map((t: any, i: number) => (
          <div key={i} className="text-sm py-2 border-b border-gray-100">
            <span className="text-xs text-gray-400">{t.ts} · {t.speaker}</span>
            <div>{t.text}</div>
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        <button className="btn btn-ghost" onClick={() => api.post(`/calls/${id}/handoff`)}>
          Human handoff
        </button>
        <button className="btn btn-ghost" onClick={() => api.post(`/calls/${id}/opt-out`)}>
          Record opt-out
        </button>
      </div>
    </div>
  );
}
