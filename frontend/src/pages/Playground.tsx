import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api";

const prompts = [
  "What services do you provide?",
  "How much does SharePoint migration cost?",
  "We already have an internal IT team.",
  "We are interested.",
  "I want a callback.",
  "I am not interested.",
  "We are looking for SharePoint migration support and want to start this month.",
];

export default function Playground() {
  const { id } = useParams();
  const [lang, setLang] = useState("en");
  const [history, setHistory] = useState<any[]>([]);
  const [input, setInput] = useState("");
  const [qual, setQual] = useState<any>(null);

  useEffect(() => {
    setHistory([]);
    setQual(null);
  }, [id, lang]);

  async function send(text: string) {
    const { data } = await api.post(`/voice-agents/${id}/playground`, { message: text, history, language: lang });
    setHistory(data.history);
    setQual(data.qualification);
    setInput("");
  }

  return (
    <div className="grid lg:grid-cols-3 gap-5">
      <div className="lg:col-span-2 card p-5 flex flex-col h-[75vh] bg-white shadow-xs">
        <div className="flex justify-between items-center mb-3 border-b border-slate-100 pb-3">
          <div>
            <h1 className="font-bold text-slate-900 text-lg">Interactive Voice Agent Studio</h1>
            <p className="text-xs text-slate-500">Test conversational responses, qualification logic, and objection handling</p>
          </div>
          <span className="badge bg-indigo-50 text-indigo-700 border border-indigo-200">
            Interactive Studio
          </span>
        </div>
        <div className="flex items-center gap-2 mb-3">
          <label className="text-xs font-semibold text-slate-600">Language:</label>
          <select className="input max-w-[180px] h-9 text-xs font-medium" value={lang} onChange={(e) => setLang(e.target.value)}>
            <option value="en">English (US/UK/Global)</option>
            <option value="hi">Hindi (हिन्दी - IN)</option>
            <option value="gu">Gujarati (ગુજરાતી - IN)</option>
            <option value="es">Spanish (Español)</option>
            <option value="fr">French (Français)</option>
            <option value="de">German (Deutsch)</option>
          </select>
        </div>
        <div className="flex-1 overflow-auto space-y-2">
          {history.map((m, i) => (
            <div key={i} className={`max-w-[80%] rounded-2xl px-3 py-2 text-sm ${m.speaker === "agent" ? "bg-blue-50" : "bg-gray-100 ml-auto"}`}>
              <div className="text-[10px] uppercase text-gray-400">{m.speaker}</div>
              {m.text}
            </div>
          ))}
        </div>
        <div className="flex flex-wrap gap-1 my-2">
          {prompts.map((p) => (
            <button key={p} className="text-xs border border-gray-200 rounded-full px-2 py-1" onClick={() => send(p)}>
              {p}
            </button>
          ))}
        </div>
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (input) send(input);
          }}
        >
          <input className="input" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Prospect message" />
          <button className="btn btn-primary">Send</button>
        </form>
      </div>
      <div className="card p-4">
        <h2 className="font-semibold">Qualification</h2>
        {!qual && <p className="text-sm text-gray-500 mt-2">Send a message to update fields.</p>}
        {qual && (
          <div className="text-sm space-y-1 mt-3">
            {qual.high_intent && <div className="badge bg-red-50 text-red-700">HIGH INTENT PROSPECT</div>}
            <div>Interest: {qual.interest_level}</div>
            <div>Requirements: {qual.requirements || "—"}</div>
            <div>Timeline: {qual.timeline || "—"}</div>
            <div>Budget: {qual.budget || "not disclosed"}</div>
            <div>Technology: {qual.technology || "—"}</div>
            <div>Missing: {(qual.missing_information || []).join(", ") || "—"}</div>
          </div>
        )}
      </div>
    </div>
  );
}
