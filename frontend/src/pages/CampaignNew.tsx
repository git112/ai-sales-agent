import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";

export default function CampaignNew() {
  const nav = useNavigate();
  const [leads, setLeads] = useState<any[]>([]);
  const [agents, setAgents] = useState<any[]>([]);
  const [type, setType] = useState("leads_plus_calling");
  const [name, setName] = useState("SharePoint qualification");
  const [agent, setAgent] = useState("");
  const [selected, setSelected] = useState<string[]>(["lead_abc"]);
  const [schedule, setSchedule] = useState("immediate");
  const [tz, setTz] = useState("Asia/Kolkata");
  useEffect(() => {
    api.get("/leads").then((r) => setLeads(r.data));
    api.get("/voice-agents").then((r) => {
      setAgents(r.data);
      if (r.data[0]) setAgent(r.data[0].id);
    });
  }, []);
  return (
    <div className="max-w-2xl card p-6 space-y-3">
      <h1 className="text-xl font-semibold">Campaign setup</h1>
      <select className="input" value={type} onChange={(e) => setType(e.target.value)}>
        <option value="calling_only">Calling only</option>
        <option value="leads_plus_calling">Leads + calling</option>
      </select>
      <input className="input" value={name} onChange={(e) => setName(e.target.value)} />
      <select className="input" value={agent} onChange={(e) => setAgent(e.target.value)}>
        {agents.map((a) => (
          <option key={a.id} value={a.id}>
            {a.name}
          </option>
        ))}
      </select>
      <select className="input" value={schedule} onChange={(e) => setSchedule(e.target.value)}>
        <option value="immediate">Immediate</option>
        <option value="scheduled">Scheduled</option>
      </select>
      <input className="input" value={tz} onChange={(e) => setTz(e.target.value)} />
      <div className="text-sm font-medium">Leads</div>
      {leads.map((l) => (
        <label key={l.id} className="flex gap-2 text-sm">
          <input
            type="checkbox"
            checked={selected.includes(l.id)}
            onChange={(e) => setSelected(e.target.checked ? [...selected, l.id] : selected.filter((x) => x !== l.id))}
          />
          {l.company} {l.phone ? "" : "(no phone — still usable in demo simulation)"}
        </label>
      ))}
      <p className="text-xs text-gray-500">Retry policy default: 2 attempts on No Answer / Voicemail.</p>
      <button
        className="btn btn-primary"
        onClick={async () => {
          const { data } = await api.post("/campaigns", {
            name,
            campaign_type: type,
            objective: "Qualify SharePoint needs",
            agent_id: agent,
            lead_ids: selected,
            language: "en",
            schedule,
            timezone: tz,
            retry_policy: { max_attempts: 2, on: ["No Answer", "Voicemail"] },
          });
          nav(`/app/campaigns/${data.id}`);
        }}
      >
        Create
      </button>
    </div>
  );
}
