import { Link } from "react-router-dom";
import { ArrowLeft, Check, Sparkles } from "lucide-react";

export default function Pricing() {
  const tiers = [
    {
      name: "Starter",
      badge: "Self-Serve",
      desc: "Discovery + 1 autonomous voice agent",
      features: ["Enterprise opportunity discovery", "1 live Bolna voice persona", "Standard workspace isolation", "Email & webhook alerts"],
      note: "Standard workspace",
      btnClass: "btn-ghost",
      btnText: "Get Started",
    },
    {
      name: "Growth",
      badge: "Most Popular",
      desc: "Campaigns + advanced analytics",
      features: ["Everything in Starter", "Automated outreach campaigns", "Real-time qualification telemetry", "Multi-language voice switching", "CRM lead sync integration"],
      note: "Usage-based voice minutes",
      btnClass: "btn-primary",
      btnText: "Start Growth Trial",
    },
    {
      name: "Enterprise",
      badge: "Custom Scale",
      desc: "SSO, CRM sync, dedicated lines",
      features: ["Everything in Growth", "Dedicated caller IDs & SIP trunks", "Custom voice agent training", "SLA guarantees & audit logs", "Custom CRM integrations"],
      note: "Custom enterprise deployment",
      btnClass: "btn-ghost",
      btnText: "Contact Enterprise",
    },
  ];

  return (
    <div className="min-h-screen bg-slate-50/50 p-6 sm:p-8">
      <div className="max-w-5xl mx-auto py-12">
        <div className="flex items-center justify-between pb-6 border-b border-slate-200">
          <Link to="/" className="flex items-center gap-2.5">
            <span className="logo-mark">L</span>
            <span className="font-bold text-slate-900 font-display text-lg">Lumina</span>
          </Link>
          <Link to="/" className="btn btn-ghost text-xs py-2 px-3 flex items-center gap-1.5">
            <ArrowLeft className="w-3.5 h-3.5" />
            Back Home
          </Link>
        </div>

        <div className="text-center mt-12 max-w-xl mx-auto">
          <span className="badge bg-indigo-50 text-indigo-700 border border-indigo-200">Predictable Pricing</span>
          <h1 className="text-4xl font-bold text-slate-900 tracking-tight font-display mt-3">Plans Built for Scale</h1>
          <p className="text-slate-500 mt-2 text-sm">Transparent tiers for autonomous sales intelligence, signal discovery, and outbound voice qualification.</p>
        </div>

        <div className="grid md:grid-cols-3 gap-6 mt-12">
          {tiers.map((t) => (
            <div
              key={t.name}
              className={`card p-6 bg-white shadow-xs flex flex-col justify-between transition-all hover:shadow-md ${
                t.name === "Growth" ? "border-indigo-400 ring-2 ring-indigo-500/20" : ""
              }`}
            >
              <div>
                <div className="flex items-center justify-between">
                  <h2 className="font-bold text-xl text-slate-900 font-display">{t.name}</h2>
                  <span className={`badge ${t.name === "Growth" ? "bg-indigo-50 text-indigo-700 border border-indigo-200" : "bg-slate-100 text-slate-600"}`}>
                    {t.badge}
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-2">{t.desc}</p>

                <div className="mt-6 pt-5 border-t border-slate-100 space-y-2.5">
                  {t.features.map((f) => (
                    <div key={f} className="flex items-center gap-2 text-xs text-slate-700">
                      <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                      <span>{f}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-8 pt-4 border-t border-slate-100">
                <div className="text-[11px] text-slate-400 mb-3">{t.note}</div>
                <Link to="/signup" className={`btn ${t.btnClass} w-full text-xs py-2.5`}>
                  {t.btnText}
                </Link>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
