import { useState } from "react";
import { Link } from "react-router-dom";
import { Sparkles, Send, ArrowUpRight, HelpCircle } from "lucide-react";
import { api } from "../api";

const samples = [
  "Which leads should I contact today?",
  "Show high-intent leads.",
  "What happened in recent call conversations?",
  "What services are in our Knowledge Base?",
  "Which prospects requested callbacks?",
  "What should I do next?",
];

export default function Copilot() {
  const [q, setQ] = useState(samples[0]);
  const [res, setRes] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  async function askQuestion(text: string) {
    if (!text.trim()) return;
    setBusy(true);
    try {
      const { data } = await api.post("/copilot/ask", { question: text });
      setRes(data);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="max-w-3xl space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-indigo-50 text-indigo-600 border border-indigo-100">
            <Sparkles className="w-5 h-5" />
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">AI Sales Copilot</h1>
        </div>
        <p className="text-sm text-slate-500 mt-1">
          Grounded conversational intelligence. Query workspace records, pipeline status, and next best actions.
        </p>
      </div>

      {/* Suggested Chips */}
      <div>
        <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
          <HelpCircle className="w-3.5 h-3.5 text-slate-400" />
          <span>Suggested Queries</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {samples.map((s) => (
            <button
              key={s}
              className="text-xs bg-white border border-slate-200 hover:border-indigo-300 hover:text-indigo-600 rounded-full px-3 py-1.5 transition text-slate-700 shadow-xs cursor-pointer"
              onClick={() => {
                setQ(s);
                askQuestion(s);
              }}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Input Form */}
      <form
        className="card p-2 bg-white shadow-xs flex items-center gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          askQuestion(q);
        }}
      >
        <input
          className="input border-0 focus:ring-0 text-sm flex-1 h-10 px-3"
          placeholder="Ask a question about your sales pipeline..."
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <button
          className="btn btn-primary h-10 px-5 text-xs font-semibold flex items-center gap-1.5"
          disabled={busy}
        >
          {busy ? (
            <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
          ) : (
            <>
              <Send className="w-3.5 h-3.5" />
              <span>Ask Copilot</span>
            </>
          )}
        </button>
      </form>

      {/* Response Card */}
      {res && (
        <div className="card p-6 bg-white shadow-xs border-l-4 border-l-indigo-600 space-y-4 animate-in fade-in duration-150">
          <div className="flex items-center gap-2 text-xs font-bold text-indigo-600 uppercase tracking-wider">
            <Sparkles className="w-4 h-4" />
            <span>Copilot Analysis</span>
          </div>

          <p className="text-sm text-slate-800 leading-relaxed font-normal whitespace-pre-line">
            {res.answer}
          </p>

          {res.citations && res.citations.length > 0 && (
            <div className="pt-3 border-t border-slate-100">
              <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Verified Sources</div>
              <div className="flex flex-wrap gap-2">
                {res.citations.map((c: any, i: number) => (
                  <div
                    key={i}
                    className="flex items-center gap-1.5 text-xs bg-slate-50 border border-slate-200 px-2.5 py-1 rounded-lg text-slate-700"
                  >
                    <span className="font-semibold capitalize text-slate-900">{c.type}:</span>
                    <span>{c.label}</span>
                    {c.type === "opportunity" && c.id && (
                      <Link
                        className="text-indigo-600 hover:text-indigo-800 ml-1 inline-flex items-center gap-0.5 font-semibold"
                        to={`/app/opportunities/${c.id}`}
                      >
                        <span>Open</span>
                        <ArrowUpRight className="w-3 h-3" />
                      </Link>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
