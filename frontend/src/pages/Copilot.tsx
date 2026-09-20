import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

const samples = [
  "Which leads should I contact today?",
  "Show high-intent leads.",
  "Why is this opportunity high priority?",
  "Which prospects requested callbacks?",
  "What happened in today's campaigns?",
  "What should I do next?",
];

export default function Copilot() {
  const [q, setQ] = useState(samples[0]);
  const [res, setRes] = useState<any>(null);
  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-semibold">AI sales copilot</h1>
      <p className="text-sm text-gray-500">Answers are grounded in workspace JSON. Records are cited. Nothing is invented.</p>
      <div className="flex flex-wrap gap-2 mt-3">
        {samples.map((s) => (
          <button key={s} className="text-xs border rounded-full px-2 py-1" onClick={() => setQ(s)}>
            {s}
          </button>
        ))}
      </div>
      <form
        className="flex gap-2 mt-4"
        onSubmit={async (e) => {
          e.preventDefault();
          setRes((await api.post("/copilot/ask", { question: q })).data);
        }}
      >
        <input className="input" value={q} onChange={(e) => setQ(e.target.value)} />
        <button className="btn btn-primary">Ask</button>
      </form>
      {res && (
        <div className="card p-5 mt-4">
          <p>{res.answer}</p>
          <div className="mt-3 text-sm">
            {res.citations?.map((c: any, i: number) => (
              <div key={i}>
                {c.type}: {c.label} ({c.id})
                {c.type === "opportunity" && c.id && (
                  <Link className="text-blue-800 ml-2" to={`/app/opportunities/${c.id}`}>
                    Open
                  </Link>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
