import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";

const stages = ["discovered", "reviewed", "contacted", "qualified", "meeting", "proposal", "won", "lost"];

export default function LeadDetail() {
  const { id } = useParams();
  const [data, setData] = useState<any>(null);
  const [notes, setNotes] = useState("");
  const [stage, setStage] = useState("");
  const [qual, setQual] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [msg, setMsg] = useState("");

  async function load() {
    const { data } = await api.get(`/leads/${id}`);
    setData(data);
    setNotes(data.lead.notes || "");
    setStage(data.lead.pipeline_stage || "");
    setQual(data.lead.qualification_status || "");
    setEmail(data.lead.email || "");
    setPhone(data.lead.phone || "");
  }
  useEffect(() => {
    load();
  }, [id]);
  if (!data) return <p>Loading…</p>;
  const { lead, enrichment, company } = data;

  async function save() {
    await api.patch(`/leads/${id}`, { notes, pipeline_stage: stage, qualification_status: qual, email: email || null, phone: phone || null });
    setMsg("Saved");
    load();
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">{lead.company}</h1>
      <span className="badge bg-amber-50 text-amber-800">DEMO DATA</span>
      <p className="text-gray-600">
        {lead.name || "Not detected"} · {lead.job_title || "Not detected"} · score {lead.opportunity_score ?? "Not detected"} · intent {lead.intent_level}
      </p>
      <div className="grid md:grid-cols-2 gap-3">
        <div className="card p-4 text-sm space-y-1">
          <div className="font-semibold">Lead</div>
          <div>Source: {lead.source} · URL: {lead.website || "Not detected"}</div>
          <div>Industry: {lead.industry || "Not detected"}</div>
          <div>Location: {lead.location || "Not detected"}</div>
        </div>
        <div className="card p-4 text-sm space-y-1">
          <div className="font-semibold">Company</div>
          <div>{company?.name || "Not detected"} · size {company?.company_size || "Not detected"}</div>
          <div>Tech: {(company?.technologies || []).join(", ") || "Not detected"}</div>
        </div>
      </div>
      <div className="card p-4 space-y-2">
        <h2 className="font-semibold">Edit</h2>
        <textarea className="input h-24" value={notes} onChange={(e) => setNotes(e.target.value)} />
        <select className="input" value={stage} onChange={(e) => setStage(e.target.value)}>
          {stages.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
        <input className="input" value={qual} onChange={(e) => setQual(e.target.value)} placeholder="Qualification status" />
        <input className="input" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" />
        <input className="input" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="Phone" />
        <button className="btn btn-primary" onClick={save}>
          Save
        </button>
        {msg && <p className="text-sm text-green-700">{msg}</p>}
      </div>
      <div className="grid md:grid-cols-2 gap-3">
        {Object.entries(enrichment).map(([k, v]: any) => (
          <div key={k} className="card p-4">
            <div className="text-xs text-gray-500">{k}</div>
            <div className="text-sm mt-1">{typeof v.value === "object" ? JSON.stringify(v.value) : v.value || v.note || "Not detected"}</div>
            <div className="text-xs text-gray-400 mt-2">
              Source: {v.source || "—"} · Confidence: {v.confidence ?? "—"} · Updated: {v.last_updated || "—"}
            </div>
          </div>
        ))}
      </div>
      <div className="card p-4">
        <h2 className="font-semibold">Calls</h2>
        {(data.calls || []).map((c: any) => (
          <Link key={c.id} className="block text-sm text-blue-800 py-1" to={`/app/calls/${c.id}`}>
            {c.outcome} · {c.label}
          </Link>
        ))}
        {!(data.calls || []).length && <p className="text-sm text-gray-500">No calls</p>}
      </div>
      <div className="card p-4">
        <h2 className="font-semibold">Tasks</h2>
        {(data.tasks || []).map((t: any) => (
          <div key={t.id} className="text-sm">
            {t.title} · {t.status}
          </div>
        ))}
      </div>
      <div className="card p-4">
        <h2 className="font-semibold">Campaigns</h2>
        {(data.campaigns || []).map((c: any) => (
          <Link key={c.id} className="block text-sm text-blue-800" to={`/app/campaigns/${c.id}`}>
            {c.name}
          </Link>
        ))}
      </div>
      <div className="card p-4">
        <h2 className="font-semibold">Activity timeline</h2>
        {data.timeline.map((t: any, i: number) => (
          <div key={i} className="text-sm py-1">
            {t.at} — {t.text}
          </div>
        ))}
      </div>
    </div>
  );
}
