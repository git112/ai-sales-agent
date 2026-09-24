import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";

const tabs = ["Overview", "Why Match", "Why Now", "Opportunity DNA", "Evidence", "Enrichment", "Market Intelligence", "Qualification", "Calls", "Timeline", "Next Best Action"];

export default function OpportunityDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const [tab, setTab] = useState("Opportunity DNA");
  const [data, setData] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [addingLead, setAddingLead] = useState(false);
  const [leadMsg, setLeadMsg] = useState("");

  async function load() {
    const { data } = await api.get(`/opportunities/${id}`);
    setData(data);
  }
  useEffect(() => {
    load();
  }, [id]);

  if (!data) return <p>Loading…</p>;
  const o = data.opportunity;
  const score = o.score || {};

  return (
    <div className="space-y-4">
      <div className="flex justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-display text-3xl font-bold text-slate-900">{o.title}</h1>
            <span className="badge bg-emerald-50 text-emerald-700 border border-emerald-200">Verified Signal</span>
          </div>
          <p className="text-slate-600 mt-1">{o.requirement}</p>
        </div>
        <div className="card px-6 py-5 text-center min-w-[160px] bg-white border border-slate-200 shadow-xs">
          <div className="text-xs text-slate-500 font-semibold tracking-wider uppercase">Opportunity Score</div>
          <div className="text-5xl font-black text-indigo-600 mt-1">{score.total ?? "—"}</div>
          <div className="text-[11px] text-slate-400 mt-1">/ 100 · AI qualified</div>
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        <button
          className="btn btn-ghost"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            await api.post(`/opportunities/${id}/analyze`);
            await load();
            setBusy(false);
          }}
        >
          Analyze
        </button>
        {/* Add to Leads button */}
        {data.lead ? (
          <button
            className="btn btn-ghost text-emerald-700 border-emerald-300 bg-emerald-50"
            onClick={() => nav(`/app/leads/${data.lead.id}`)}
          >
            ✓ View Lead
          </button>
        ) : (
          <button
            className="btn btn-ghost"
            disabled={addingLead}
            onClick={async () => {
              setAddingLead(true);
              setLeadMsg("");
              try {
                const { data: res } = await api.post(`/opportunities/${id}/add-lead`);
                setLeadMsg(res.message);
                await load();
              } catch (e: any) {
                setLeadMsg(e.response?.data?.error?.message || "Failed to add lead");
              } finally {
                setAddingLead(false);
              }
            }}
          >
            {addingLead ? "Adding…" : "+ Add to Leads"}
          </button>
        )}
        <button
          className="btn btn-primary"
          onClick={async () => {
            const agents = (await api.get("/voice-agents")).data;
            // Ensure a lead exists first
            let leadId = data.lead?.id;
            if (!leadId) {
              const { data: res } = await api.post(`/opportunities/${id}/add-lead`);
              leadId = res.lead.id;
              await load();
            }
            const { data: camp } = await api.post("/campaigns", {
              name: `Qualify ${data.opportunity?.company_name || data.opportunity?.company || "prospect"}`,
              campaign_type: "leads_plus_calling",
              objective: "Qualify SharePoint interest",
              agent_id: agents[0]?.id,
              lead_ids: leadId ? [leadId] : [],
              language: "en",
              schedule: "immediate",
              timezone: "Asia/Kolkata",
            });
            await api.post(`/campaigns/${camp.id}/launch`);
            nav(`/app/campaigns/${camp.id}`);
          }}
        >
          Start campaign
        </button>
        {leadMsg && <span className="text-sm text-emerald-700 font-medium self-center">{leadMsg}</span>}
      </div>
      <div className="flex flex-wrap gap-1 border-b border-gray-200">
        {tabs.map((t) => (
          <button key={t} className={`px-3 py-2 text-sm ${tab === t ? "border-b-2 border-blue-700 font-semibold" : "text-gray-500"}`} onClick={() => setTab(t)}>
            {t}
          </button>
        ))}
      </div>

      {tab === "Overview" && (
        <div className="grid md:grid-cols-2 gap-4">
          <Field label="Company" value={data.company?.name} />
          <Field label="Requirement" value={o.requirement} />
          <Field label="Source" value={o.source} />
          <Field label="Original URL" value={o.source_url} />
          <Field label="Date" value={o.published_at} />
          <Field
            label="Contact"
            value={
              data.contact
                ? `${data.contact.name} · ${data.contact.email} · ${data.contact.phone}`
                : "Contact information not publicly available."
            }
          />
        </div>
      )}
      {tab === "Why Match" && (
        <Block title="Why this matches" body={o.why_match} evidence={data.signals} />
      )}
      {tab === "Why Now" && <Block title="Why now" body={o.why_now} evidence={data.signals.filter((s: any) => ["Hiring", "Requirement", "Business announcement"].includes(s.signal_type))} />}
      {tab === "Opportunity DNA" && <DNA o={o} company={data.company} signals={data.signals} score={score} />}
      {tab === "Evidence" && <EvidenceList items={data.signals} />}
      {tab === "Enrichment" && (
        <div className="grid md:grid-cols-2 gap-3">
          {[
            ["Industry", data.company?.industry, data.company?.source, data.company?.confidence],
            ["Size", data.company?.company_size, data.company?.source, data.company?.confidence],
            ["Location", data.company?.location, data.company?.source, data.company?.confidence],
            ["Technology", (data.company?.technologies || []).join(", "), data.company?.source, data.company?.confidence],
          ].map(([l, v, s, c]) => (
            <div key={String(l)} className="card p-4">
              <div className="text-xs text-gray-500">{l}</div>
              <div className="font-medium">{v || "Not detected"}</div>
              <div className="text-xs text-gray-400 mt-1">
                Source: {String(s)} · Confidence {String(c)} · Updated {data.company?.last_updated}
              </div>
            </div>
          ))}
        </div>
      )}
      {tab === "Market Intelligence" && (
        <div className="space-y-3">
          {(data.market_intelligence || []).map((m: any) => (
            <div key={m.id} className="card p-4">
              <div className="text-xs uppercase text-gray-400">{m.kind}</div>
              <div className="font-medium">{m.detected ? m.summary : "Signal was not detected."}</div>
              <div className="text-xs text-gray-500 mt-1">
                Source: {m.source || "—"} · Confidence: {m.confidence ?? "—"} · Updated: {m.last_updated}
              </div>
              {m.evidence && <p className="text-sm text-gray-600 mt-2">{m.evidence}</p>}
              {m.source_url && (
                <a className="text-xs text-blue-700" href={m.source_url} target="_blank" rel="noreferrer">
                  {m.source_url}
                </a>
              )}
            </div>
          ))}
        </div>
      )}
      {tab === "Qualification" && (
        <div className="space-y-3">
          {data.qualifications.length === 0 && <p className="text-sm text-slate-400 py-4 text-center">No qualification recorded yet. Initiate outreach from the campaign console.</p>}
          {data.qualifications.map((q: any) => (
            <div key={q.id} className="card p-4">
              {q.high_intent && <div className="badge bg-red-50 text-red-700 mb-2">HIGH INTENT PROSPECT</div>}
              <div className="text-sm">Interest: {q.interest_level}</div>
              <div className="text-sm">Requirements: {q.requirements || "—"}</div>
              <div className="text-sm">Timeline: {q.timeline || "—"}</div>
            </div>
          ))}
        </div>
      )}
      {tab === "Calls" && (
        <div>
          {data.calls.map((c: any) => (
            <Link key={c.id} to={`/app/calls/${c.id}`} className="card p-4 block mb-2">
              {c.outcome} · {c.label} · {c.started_at}
            </Link>
          ))}
          {data.calls.length === 0 && <p className="text-sm text-gray-500">No calls yet.</p>}
        </div>
      )}
      {tab === "Timeline" && (
        <ul className="text-sm space-y-2">
          <li>Discovered {o.discovered_at}</li>
          <li>Published {o.published_at}</li>
          {data.calls.map((c: any) => (
            <li key={c.id}>Call {c.outcome} {c.started_at}</li>
          ))}
        </ul>
      )}
      {tab === "Next Best Action" && (
        <div className="card p-5">
          <div className="text-xs text-gray-500">ACTION</div>
          <div className="text-xl font-semibold">{data.next_best_action?.action || "—"}</div>
          <div className="mt-3 text-sm">
            <strong>WHY</strong> {data.next_best_action?.why}
          </div>
          <div className="mt-2 text-sm">
            <strong>PRIORITY</strong> {data.next_best_action?.priority}
          </div>
          <div className="mt-2 text-xs text-gray-500">EVIDENCE must come from transcripts or public signals — never invented.</div>
        </div>
      )}
    </div>
  );
}

function Field({ label, value }: { label: string; value: string | undefined }) {
  return (
    <div className="card p-4">
      <div className="text-xs text-gray-500">{label}</div>
      <div className="mt-1 break-all">{value || "—"}</div>
    </div>
  );
}

function Block({ title, body, evidence }: { title: string; body: string; evidence: any[] }) {
  return (
    <div className="card p-5">
      <h3 className="font-semibold">{title}</h3>
      <p className="mt-2 text-gray-800">{body}</p>
      <h4 className="text-sm font-semibold mt-4">Evidence</h4>
      {(!evidence || evidence.length === 0) && <p className="text-sm text-gray-500">Insufficient evidence.</p>}
      {evidence?.map((s: any) => (
        <p key={s.id} className="text-sm text-gray-600 mt-1">
          “{(s.evidence && s.evidence[0]?.quote) || s.title}” — {s.source} · {s.source_url}
        </p>
      ))}
    </div>
  );
}

function EvidenceList({ items }: { items: any[] }) {
  return (
    <div className="space-y-3">
      {items.map((s) => (
        <div key={s.id} className="card p-4">
          <div className="text-xs text-blue-800 font-semibold">{s.signal_type}</div>
          <div className="font-medium">{s.title}</div>
          <p className="text-sm text-gray-600">{s.description}</p>
          <a className="text-xs text-blue-700" href={s.source_url} target="_blank" rel="noreferrer">
            {s.source_url}
          </a>
        </div>
      ))}
    </div>
  );
}

function DNA({ o, company, signals, score }: any) {
  const rows = [
    ["Company", company?.name],
    ["Requirement", o.requirement],
    ["Need", o.need],
    ["Technology", (o.technology || []).join(", ")],
    ["Industry", o.industry],
    ["Location", o.location],
    ["Timeline", o.timeline],
    ["Budget", o.budget || o.budget_note],
  ];
  return (
    <div className="grid lg:grid-cols-3 gap-4">
      <div className="lg:col-span-2 card p-6">
        <h3 className="font-display text-2xl">Opportunity DNA</h3>
        <div className="grid md:grid-cols-2 gap-4 mt-4">
          {rows.map(([k, v]) => (
            <div key={k}>
              <div className="text-xs uppercase tracking-wide text-gray-400">{k}</div>
              <div className="text-sm mt-1">{v}</div>
            </div>
          ))}
        </div>
        <div className="mt-6">
          <div className="text-xs uppercase text-gray-400">Buying signals</div>
          <div className="flex flex-wrap gap-2 mt-2">
            {signals.map((s: any) => (
              <span key={s.id} className="badge bg-blue-50 text-blue-800">
                {s.signal_type}
              </span>
            ))}
          </div>
        </div>
        <div className="grid md:grid-cols-2 gap-4 mt-6">
          <div>
            <div className="text-xs uppercase text-gray-400">Why match</div>
            <p className="text-sm mt-1">{o.why_match}</p>
          </div>
          <div>
            <div className="text-xs uppercase text-gray-400">Why now</div>
            <p className="text-sm mt-1">{o.why_now}</p>
          </div>
        </div>
        <div className="mt-4 text-sm">
          <strong>Risks:</strong> {(o.risks || []).join(" ")}
        </div>
        <div className="text-sm">
          <strong>Missing:</strong> {(o.missing_information || []).join(", ")}
        </div>
        <div className="mt-3 text-sm font-medium text-blue-900">Recommended: {o.recommended_action}</div>
      </div>
      <div className="card p-6">
        <div className="text-xs text-gray-500">Score breakdown</div>
        {[
          ["Service match", score.service_match],
          ["Intent", score.intent_score],
          ["Freshness", score.freshness_score],
          ["Technology", score.technology_match],
          ["Company fit", score.company_fit],
        ].map(([k, v]) => (
          <div key={k} className="mt-3">
            <div className="flex justify-between text-xs">
              <span>{k}</span>
              <span>{v}</span>
            </div>
              <div className="h-2 bg-gray-100 rounded-full mt-1 overflow-hidden">
                <div className="h-2 rounded-full bg-gradient-to-r from-[#b8862b] to-[#f3d48a]" style={{ width: `${v || 0}%` }} />
              </div>
          </div>
        ))}
        <p className="text-[11px] text-gray-400 mt-4">{score.disclaimer}</p>
        <div className="mt-4">
          <h4 className="text-sm font-semibold">Market intelligence</h4>
          <p className="text-xs text-gray-500">Open Enrichment / signals. Funding is marked not detected when absent.</p>
        </div>
      </div>
    </div>
  );
}
