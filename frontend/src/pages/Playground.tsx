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
    <div className="grid lg:grid-cols-3 gap-4">
      <div className="lg:col-span-2 card p-4 flex flex-col h-[70vh]">
        <div className="flex justify-between items-center mb-3">
          <h1 className="font-semibold">Voice agent playground</h1>
          <span className="badge bg-amber-50 text-amber-800">Demo Voice Simulation</span>
        </div>
        <select className="input max-w-[160px] mb-3" value={lang} onChange={(e) => setLang(e.target.value)}>
          <option value="en">English</option>
          <option value="hi">Hindi</option>
          <option value="gu">Gujarati</option>
        </select>
        <div className="flex-1 overflow-auto space-y-2">
          {history.map((m, i) => (
            <div key={i} className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${m.speaker === "agent" ? "bg-blue-50" : "bg-gray-100 ml-auto"}`}>
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
