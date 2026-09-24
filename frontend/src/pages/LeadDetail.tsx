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
    <div className="space-y-5 max-w-4xl">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold text-slate-900">{lead.company}</h1>
            <span className="badge bg-indigo-50 text-indigo-700 border border-indigo-200">
              {lead.pipeline_stage || "Discovered"}
            </span>
          </div>
          <p className="text-slate-500 text-sm mt-1">
            {lead.name || "Primary Contact"} · {lead.job_title || "Decision Maker"} · Score: <strong className="text-indigo-600">{lead.opportunity_score ?? "—"}</strong> · Intent: {lead.intent_level}
          </p>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <div className="card p-5 text-sm space-y-2 bg-white shadow-xs">
          <div className="font-bold text-slate-900 border-b border-slate-100 pb-2">Prospect Intelligence</div>
          <div className="text-slate-600"><span className="text-slate-400">Source:</span> {lead.source}</div>
          <div className="text-slate-600"><span className="text-slate-400">Website:</span> {lead.website || "—"}</div>
          <div className="text-slate-600"><span className="text-slate-400">Industry:</span> {lead.industry || "Enterprise"}</div>
          <div className="text-slate-600"><span className="text-slate-400">Location:</span> {lead.location || "Global"}</div>
        </div>

        <div className="card p-5 text-sm space-y-2 bg-white shadow-xs">
          <div className="font-bold text-slate-900 border-b border-slate-100 pb-2">Company Background</div>
          <div className="text-slate-600"><span className="text-slate-400">Organization:</span> {company?.name || lead.company}</div>
          <div className="text-slate-600"><span className="text-slate-400">Scale:</span> {company?.company_size || "Mid-Market / Enterprise"}</div>
          <div className="text-slate-600"><span className="text-slate-400">Stack:</span> {(company?.technologies || []).join(", ") || "Cloud Architecture"}</div>
        </div>
      </div>

      <div className="card p-5 space-y-4 bg-white shadow-xs">
        <h2 className="font-bold text-slate-900 text-base">Edit Prospect Profile</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Pipeline Stage</label>
            <select className="input h-10 text-xs font-medium" value={stage} onChange={(e) => setStage(e.target.value)}>
              {stages.map((s) => (
                <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Qualification Status</label>
            <input className="input h-10 text-xs" value={qual} onChange={(e) => setQual(e.target.value)} placeholder="e.g. Scheduled meeting" />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Contact Email</label>
            <input className="input h-10 text-xs" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@company.com" />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Contact Phone</label>
            <input className="input h-10 text-xs" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+1 555-0100" />
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">Internal Notes & Context</label>
          <textarea className="input h-20 text-xs" value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Add sales notes..." />
        </div>

        <div className="flex items-center gap-3 pt-1">
          <button className="btn btn-primary text-xs px-5" onClick={save}>
            Save Changes
          </button>
          {msg && <p className="text-xs font-semibold text-emerald-600">{msg}</p>}
        </div>
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
