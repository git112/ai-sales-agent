import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Bot, ArrowLeft, Play, Save, CheckCircle2, ShieldAlert } from "lucide-react";
import { api } from "../api";

export default function AgentDetail() {
  const { id } = useParams();
  const [agent, setAgent] = useState<any>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api.get(`/voice-agents/${id}`).then((r) => setAgent(r.data));
  }, [id]);

  if (!agent) {
    return (
      <div className="flex items-center justify-center min-h-[300px] text-slate-500 text-sm">
        <div className="w-4 h-4 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin mr-2"></div>
        Loading agent configuration…
      </div>
    );
  }

  const handleSave = async () => {
    const res = await api.patch(`/voice-agents/${id}`, agent);
    setAgent(res.data);
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div className="max-w-3xl space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link
          to="/app/agents"
          className="p-2 rounded-xl bg-white border border-slate-200 text-slate-500 hover:text-slate-800 transition shadow-xs"
        >
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">{agent.name}</h1>
            <span className="badge bg-indigo-50 text-indigo-700 border border-indigo-200 uppercase">{agent.language}</span>
          </div>
          <p className="text-sm text-slate-500 mt-0.5">{agent.purpose}</p>
        </div>
      </div>

      <div className="card p-6 bg-white shadow-xs space-y-5">
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-xs">
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
            <span className="text-slate-400 block font-medium mb-1">Language</span>
            <span className="font-bold text-slate-800 uppercase">{agent.language}</span>
          </div>
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
            <span className="text-slate-400 block font-medium mb-1">Voice Persona</span>
            <span className="font-bold text-slate-800 capitalize">{agent.voice || "Natural"}</span>
          </div>
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
            <span className="text-slate-400 block font-medium mb-1">Conversational Tone</span>
            <span className="font-bold text-slate-800 capitalize">{agent.tone || "Professional"}</span>
          </div>
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 col-span-2">
            <span className="text-slate-400 block font-medium mb-1">Call Objective</span>
            <span className="font-semibold text-slate-800">{agent.call_objective || "Lead Qualification"}</span>
          </div>
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
            <span className="text-slate-400 block font-medium mb-1">AI Disclosure</span>
            <span className="font-semibold text-slate-800">{agent.safety?.disclose_ai ? "Required" : "Optional"}</span>
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1.5">Approved Voicemail Message</label>
          <textarea
            className="input min-h-[90px] text-xs font-normal"
            value={agent.approved_voicemail || ""}
            onChange={(e) => setAgent({ ...agent, approved_voicemail: e.target.value })}
            placeholder="Scripted voicemail message left when call is not answered..."
          />
        </div>

        <div className="flex items-center justify-between pt-2 border-t border-slate-100">
          <div className="flex items-center gap-2">
            <button className="btn btn-primary text-xs py-2 px-4 flex items-center gap-1.5" onClick={handleSave}>
              <Save className="w-3.5 h-3.5" />
              Save Configuration
            </button>
            {saved && (
              <span className="text-xs text-emerald-700 font-medium flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> Saved
              </span>
            )}
          </div>

          <Link className="btn btn-ghost text-xs py-2 px-4 flex items-center gap-1.5 text-indigo-600" to={`/app/agents/${id}/playground`}>
            <Play className="w-3.5 h-3.5" />
            Launch Studio Playground
          </Link>
        </div>
      </div>
    </div>
  );
}
