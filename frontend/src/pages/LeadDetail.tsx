import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api";

export default function LeadDetail() {
  const { id } = useParams();
  const [data, setData] = useState<any>(null);
  useEffect(() => {
    api.get(`/leads/${id}`).then((r) => setData(r.data));
  }, [id]);
  if (!data) return <p>Loading…</p>;
  const { lead, enrichment } = data;
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">{lead.company}</h1>
      <p className="text-gray-600">
        {lead.name} · {lead.job_title} · {lead.pipeline_stage}
      </p>
      <div className="grid md:grid-cols-2 gap-3">
        {Object.entries(enrichment).map(([k, v]: any) => (
          <div key={k} className="card p-4">
            <div className="text-xs text-gray-500">{k}</div>
            <div className="text-sm mt-1">{typeof v.value === "object" ? JSON.stringify(v.value) : v.value || v.note || "Not available"}</div>
            <div className="text-xs text-gray-400 mt-2">
              Source: {v.source || "—"} · Confidence: {v.confidence ?? "—"} · Updated: {v.last_updated || "—"}
            </div>
          </div>
        ))}
      </div>
      <div className="card p-4">
        <h2 className="font-semibold">Timeline</h2>
        {data.timeline.map((t: any, i: number) => (
          <div key={i} className="text-sm py-1">
            {t.at} — {t.text}
          </div>
        ))}
      </div>
    </div>
  );
}
