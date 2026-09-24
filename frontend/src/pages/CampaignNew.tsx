import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Megaphone, ArrowLeft, Bot, Calendar, Clock, CheckCircle2 } from "lucide-react";
import { api } from "../api";

export default function CampaignNew() {
  const nav = useNavigate();
  const [leads, setLeads] = useState<any[]>([]);
  const [agents, setAgents] = useState<any[]>([]);
  const [type, setType] = useState("leads_plus_calling");
  const [name, setName] = useState("SharePoint Qualification Campaign");
  const [agent, setAgent] = useState("");
  const [selected, setSelected] = useState<string[]>(["lead_abc"]);
  const [schedule, setSchedule] = useState("immediate");
  const [tz, setTz] = useState("Asia/Kolkata");
  const [retry, setRetry] = useState(3);
  const [quietStart, setQuietStart] = useState("21:00");
  const [quietEnd, setQuietEnd] = useState("08:00");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    api.get("/leads").then((r) => setLeads(r.data));
    api.get("/voice-agents").then((r) => {
      setAgents(r.data);
      if (r.data[0]) setAgent(r.data[0].id);
    });
  }, []);

  return (
    <div className="max-w-3xl space-y-6">
      <div className="flex items-center gap-3">
        <button
          onClick={() => nav("/app/campaigns")}
          className="p-2 rounded-xl bg-white border border-slate-200 text-slate-500 hover:text-slate-800 transition shadow-xs"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Create Outreach Campaign</h1>
          <p className="text-sm text-slate-500">Configure autonomous outbound calling and qualification rules.</p>
        </div>
      </div>

      <div className="card p-6 bg-white shadow-xs space-y-5">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Campaign Name</label>
            <input className="input h-10" value={name} onChange={(e) => setName(e.target.value)} />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Campaign Architecture</label>
            <select className="input h-10 text-xs font-medium" value={type} onChange={(e) => setType(e.target.value)}>
              <option value="leads_plus_calling">Discovery + Calling (Full Funnel)</option>
              <option value="calling_only">Direct Calling Only</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Assigned Voice Agent</label>
            <select className="input h-10 text-xs font-medium" value={agent} onChange={(e) => setAgent(e.target.value)}>
              {agents.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name} ({a.language || "Multilingual"})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Execution Schedule</label>
            <select className="input h-10 text-xs font-medium" value={schedule} onChange={(e) => setSchedule(e.target.value)}>
              <option value="immediate">Immediate Launch</option>
              <option value="scheduled">Scheduled Queue</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Timezone</label>
            <input className="input h-10 text-xs" value={tz} onChange={(e) => setTz(e.target.value)} />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Max Retry Attempts</label>
            <input className="input h-10 text-xs" type="number" value={retry} onChange={(e) => setRetry(+e.target.value)} />
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">Quiet Hours Window (Calls suppressed)</label>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <span className="text-[11px] text-slate-400">Quiet Start</span>
              <input className="input h-10 text-xs" value={quietStart} onChange={(e) => setQuietStart(e.target.value)} />
            </div>
            <div>
              <span className="text-[11px] text-slate-400">Quiet End</span>
              <input className="input h-10 text-xs" value={quietEnd} onChange={(e) => setQuietEnd(e.target.value)} />
            </div>
          </div>
        </div>

        <div className="pt-2">
          <label className="block text-xs font-semibold text-slate-700 mb-2">Select Target Leads ({selected.length} chosen)</label>
          <div className="max-h-48 overflow-y-auto space-y-1.5 border border-slate-200 rounded-xl p-3 bg-slate-50/50">
            {leads.map((l) => (
              <label key={l.id} className="flex items-center gap-2.5 text-xs text-slate-700 hover:bg-white p-1.5 rounded-lg cursor-pointer transition">
                <input
                  type="checkbox"
                  className="rounded text-indigo-600 focus:ring-indigo-500"
                  checked={selected.includes(l.id)}
                  onChange={(e) => setSelected(e.target.checked ? [...selected, l.id] : selected.filter((x) => x !== l.id))}
                />
                <span className="font-semibold text-slate-900">{l.company}</span>
                <span className="text-slate-400">({l.name || "Main Contact"} · {l.pipeline_stage})</span>
              </label>
            ))}
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
          <button className="btn btn-ghost text-xs" onClick={() => nav("/app/campaigns")}>
            Cancel
          </button>
          <button
            className="btn btn-primary text-xs px-5"
            disabled={creating}
            onClick={async () => {
              setCreating(true);
              try {
                const { data } = await api.post("/campaigns", {
                  name,
                  campaign_type: type,
                  objective: "Qualify SharePoint needs",
                  agent_id: agent,
                  lead_ids: selected,
                  language: "en",
                  schedule,
                  timezone: tz,
                  quiet_hours: { start: quietStart, end: quietEnd },
                  retry_policy: {
                    max_attempts: retry,
                    interval_minutes: 60,
                    on: ["No Answer", "Voicemail"],
                    sequence: ["No Answer", "Voicemail", "Interested"],
                  },
                });
                nav(`/app/campaigns/${data.id}`);
              } finally {
                setCreating(false);
              }
            }}
          >
            {creating ? "Launching…" : "Create & Launch Campaign"}
          </button>
        </div>
      </div>
    </div>
  );
}
