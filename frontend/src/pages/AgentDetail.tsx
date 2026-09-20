import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";

export default function AgentDetail() {
  const { id } = useParams();
  const [agent, setAgent] = useState<any>(null);
  useEffect(() => {
    api.get(`/voice-agents/${id}`).then((r) => setAgent(r.data));
  }, [id]);
  if (!agent) return <p>Loading…</p>;
  return (
    <div className="max-w-2xl space-y-4">
      <h1 className="text-2xl font-semibold">{agent.name}</h1>
      <p className="text-gray-600">{agent.purpose}</p>
      <div className="card p-4 text-sm space-y-1">
        <div>Language: {agent.language}</div>
        <div>Voice: {agent.voice}</div>
        <div>Tone: {agent.tone}</div>
        <div>Objective: {agent.call_objective}</div>
        <div>AI disclosure: {agent.safety?.disclose_ai ? "required" : "off"}</div>
      </div>
      <textarea
        className="input h-24"
        value={agent.approved_voicemail || ""}
        onChange={(e) => setAgent({ ...agent, approved_voicemail: e.target.value })}
      />
      <div className="flex gap-2">
        <button className="btn btn-ghost" onClick={() => api.patch(`/voice-agents/${id}`, agent).then((r) => setAgent(r.data))}>
          Save
        </button>
        <Link className="btn btn-primary" to={`/app/agents/${id}/playground`}>
          Test playground
        </Link>
      </div>
    </div>
  );
}
