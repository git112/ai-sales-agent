import { Link } from "react-router-dom";

export default function Pricing() {
  return (
    <div className="min-h-screen p-6">
      <div className="max-w-5xl mx-auto px-6 py-16">
        <div className="flex justify-between">
          <Link to="/" className="text-sm text-blue-800">
            Lumina
          </Link>
        </div>
        <h1 className="text-3xl font-semibold mt-4">Pricing Plans</h1>
        <p className="text-slate-500 mt-2">Transparent tiers for autonomous sales intelligence and outreach.</p>
        <div className="grid md:grid-cols-3 gap-4 mt-10">
          {[
            ["Starter", "Discovery + 1 autonomous voice agent", "Standard workspace"],
            ["Growth", "Campaigns + advanced analytics", "Usage-based voice minutes"],
            ["Enterprise", "SSO, CRM sync, dedicated lines", "Custom deployment"],
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
