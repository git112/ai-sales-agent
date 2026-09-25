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
    <div className="space-y-4">
      <div className="grid lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 card p-5 flex flex-col h-[75vh] bg-white shadow-xs">
          <div className="flex justify-between items-center mb-3 border-b border-slate-100 pb-3">
            <div>
              <h1 className="font-bold text-slate-900 text-lg font-display">Interactive Voice Agent Studio</h1>
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
          <div className="flex-1 overflow-auto space-y-2.5 p-1">
            {history.length === 0 && (
              <div className="h-full flex items-center justify-center text-center p-6 text-slate-400 text-xs">
                Send a sample prompt below or type a message to start simulating the voice agent conversation.
              </div>
            )}
            {history.map((m, i) => (
              <div
                key={i}
                className={`max-w-[80%] rounded-2xl px-3.5 py-2.5 text-sm shadow-xs ${
                  m.speaker === "agent"
                    ? "bg-indigo-50/80 text-indigo-950 border border-indigo-100/80"
                    : "bg-slate-100 text-slate-800 ml-auto border border-slate-200/80"
                }`}
              >
                <div className={`text-[10px] font-bold uppercase tracking-wider mb-1 ${m.speaker === "agent" ? "text-indigo-600" : "text-slate-500"}`}>
                  {m.speaker}
                </div>
                <div className="leading-relaxed">{m.text}</div>
              </div>
            ))}
          </div>
          <div className="flex flex-wrap gap-1.5 my-3 pt-2 border-t border-slate-100">
            {prompts.map((p) => (
              <button
                key={p}
                className="text-xs border border-slate-200 hover:border-indigo-300 hover:text-indigo-600 bg-slate-50 hover:bg-white rounded-full px-2.5 py-1 text-slate-600 transition shadow-xs cursor-pointer"
                onClick={() => send(p)}
              >
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
            <input className="input h-10" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Type prospect message or objection..." />
            <button className="btn btn-primary h-10 px-5">Send</button>
          </form>
        </div>

        <div className="card p-5 bg-white shadow-xs space-y-3 h-fit">
          <div className="border-b border-slate-100 pb-2.5">
            <h2 className="font-bold text-slate-900 text-sm font-display">Real-Time Qualification</h2>
            <p className="text-[11px] text-slate-500">Autonomous extraction from live dialog turns</p>
          </div>
          {!qual && (
            <p className="text-xs text-slate-400 py-4 text-center">
              Send a message to populate structured qualification criteria.
            </p>
          )}
          {qual && (
            <div className="text-xs space-y-2 mt-2">
              {qual.high_intent && (
                <div className="badge bg-amber-50 text-amber-800 border border-amber-200 font-bold w-full justify-center py-1">
                  HIGH INTENT PROSPECT
                </div>
              )}
              <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-slate-400 block font-medium">Interest Level</span>
                <span className="font-bold text-slate-800 capitalize">{qual.interest_level || "Unknown"}</span>
              </div>
              <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-slate-400 block font-medium">Requirements</span>
                <span className="font-medium text-slate-800">{qual.requirements || "—"}</span>
              </div>
              <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-slate-400 block font-medium">Timeline</span>
                <span className="font-medium text-slate-800">{qual.timeline || "—"}</span>
              </div>
              <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-slate-400 block font-medium">Budget</span>
                <span className="font-medium text-slate-800">{qual.budget || "Not disclosed"}</span>
              </div>
              <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-slate-400 block font-medium">Technology</span>
                <span className="font-medium text-slate-800">{qual.technology || "—"}</span>
              </div>
              <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-100">
                <span className="text-slate-400 block font-medium">Missing Information</span>
                <span className="font-medium text-slate-800">{(qual.missing_information || []).join(", ") || "None"}</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
