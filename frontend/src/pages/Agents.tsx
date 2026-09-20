import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

export default function Agents() {
  const [rows, setRows] = useState<any[]>([]);
  const [name, setName] = useState("SharePoint Sales Agent");
  useEffect(() => {
    api.get("/voice-agents").then((r) => setRows(r.data));
  }, []);
  return (
    <div>
      <h1 className="text-2xl font-semibold">Voice agents</h1>
      <div className="card p-4 mt-4 flex gap-2">
        <input className="input" value={name} onChange={(e) => setName(e.target.value)} />
        <button
          className="btn btn-primary"
          onClick={async () => {
            await api.post("/voice-agents", {
              name,
              purpose: "Qualify companies interested in SharePoint implementation.",
              language: "en",
              voice: "professional_female",
              tone: "consultative",
              knowledge_doc_ids: ["doc_001"],
              call_objective: "Qualify need, timeline, and meeting interest.",
              qualification_questions: ["What service are you looking for?", "What is your timeline?"],
            });
            setRows((await api.get("/voice-agents")).data);
          }}
        >
          Create
        </button>
      </div>
      {rows.map((a) => (
        <div key={a.id} className="card p-4 mt-3 flex justify-between">
          <div>
            <div className="font-semibold">{a.name}</div>
            <div className="text-sm text-gray-600">{a.purpose}</div>
            <div className="text-xs text-gray-500">
              {a.language} · {a.voice} · {a.tone}
            </div>
          </div>
          <Link className="btn btn-ghost" to={`/app/agents/${a.id}`}>
            Settings
          </Link>
          <Link className="btn btn-primary" to={`/app/agents/${a.id}/playground`}>
            Test playground
          </Link>
        </div>
      ))}
    </div>
  );
}
