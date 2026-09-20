import { Link } from "react-router-dom";

export default function Pricing() {
  return (
    <div className="min-h-screen bg-white">
      <div className="max-w-5xl mx-auto px-6 py-16">
        <Link to="/" className="text-sm text-blue-800">
          Lumina
        </Link>
        <h1 className="text-3xl font-semibold mt-4">Pricing</h1>
        <p className="text-gray-600 mt-2">Hackathon display only — billing is not implemented.</p>
        <div className="grid md:grid-cols-3 gap-4 mt-10">
          {[
            ["Starter", "Discovery + 1 agent", "Demo workspace"],
            ["Growth", "Campaigns + analytics", "Usage-based voice minutes"],
            ["Enterprise", "SSO, CRM, live telephony", "Future"],
          ].map(([n, d, n2]) => (
            <div key={n} className="card p-6">
              <h2 className="font-semibold text-lg">{n}</h2>
              <p className="text-sm text-gray-600 mt-2">{d}</p>
              <p className="text-xs text-gray-400 mt-4">{n2}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
