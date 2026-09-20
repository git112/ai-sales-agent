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
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Call {call.outcome}</h1>
      <span className="badge bg-amber-50 text-amber-800">{call.label}</span>
      {call.voicemail_message && (
        <div className="card p-4">
          <div className="text-xs text-gray-500">Approved voicemail (simulation)</div>
          <p className="text-sm mt-1">{call.voicemail_message}</p>
        </div>
      )}
      {call.stop_reason && <p className="text-sm">Stopped: {call.stop_reason}</p>}
      {qualification?.high_intent && <div className="badge bg-red-50 text-red-700">HIGH INTENT PROSPECT</div>}
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
