import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bot, Plus, Play, Settings, Sparkles } from "lucide-react";
import { api } from "../api";

export default function Agents() {
  const [rows, setRows] = useState<any[]>([]);
  const [name, setName] = useState("SharePoint Sales Agent");
  const [creating, setCreating] = useState(false);

  async function load() {
    const { data } = await api.get("/voice-agents");
    setRows(data);
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-indigo-50 text-indigo-600 border border-indigo-100">
            <Bot className="w-5 h-5" />
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">AI Voice Agents</h1>
        </div>
        <p className="text-sm text-slate-500 mt-1">
          Configure conversational personas, qualification questions, scripts, and language localization.
        </p>
      </div>

      {/* Quick Agent Creator */}
      <div className="card p-5 bg-white shadow-xs space-y-3">
        <h2 className="font-bold text-slate-900 text-sm uppercase tracking-wider flex items-center gap-2">
          <Plus className="w-4 h-4 text-indigo-600" />
          Deploy New Voice Agent
        </h2>
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
          <div className="flex-1">
            <input
              className="input h-10"
              placeholder="e.g. Enterprise Cloud Sales Agent"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <button
            className="btn btn-primary h-10 px-5 text-xs font-semibold flex items-center gap-1.5"
            disabled={creating}
            onClick={async () => {
              if (!name.trim()) return;
              setCreating(true);
              try {
                await api.post("/voice-agents", {
                  name,
                  purpose: "Qualify companies interested in SharePoint and enterprise software solutions.",
                  language: "en",
                  voice: "professional_female",
                  tone: "consultative",
                  knowledge_doc_ids: ["doc_001"],
                  call_objective: "Qualify technical requirements, timeline, and decision maker availability.",
                  qualification_questions: ["What service are you looking for?", "What is your migration timeline?"],
                });
                setName("");
                load();
              } finally {
                setCreating(false);
              }
            }}
          >
            <Plus className="w-4 h-4" />
            <span>{creating ? "Creating…" : "Deploy Agent"}</span>
          </button>
        </div>
      </div>

      {/* Agents List */}
      <div className="space-y-3">
        {rows.map((a) => (
          <div
            key={a.id}
            className="card p-5 bg-white shadow-xs hover:border-slate-300 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4"
          >
            <div className="space-y-1.5">
              <div className="flex items-center gap-2">
                <span className="font-bold text-slate-900 text-base">{a.name}</span>
                <span className="badge bg-indigo-50 text-indigo-700 border border-indigo-200">
                  {a.language || "English"}
                </span>
              </div>
              <p className="text-xs text-slate-600 max-w-xl">{a.purpose}</p>
              <div className="flex items-center gap-4 text-xs text-slate-400 pt-1">
                <span>Voice: <strong className="text-slate-700 font-medium">{a.voice || "Professional"}</strong></span>
                <span>Tone: <strong className="text-slate-700 font-medium">{a.tone || "Consultative"}</strong></span>
              </div>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <Link className="btn btn-ghost text-xs py-2 px-3 flex items-center gap-1.5" to={`/app/agents/${a.id}`}>
                <Settings className="w-3.5 h-3.5 text-slate-500" />
                <span>Config</span>
              </Link>
              <Link className="btn btn-primary text-xs py-2 px-3 flex items-center gap-1.5" to={`/app/agents/${a.id}/playground`}>
                <Play className="w-3.5 h-3.5" />
                <span>Test Studio</span>
              </Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
