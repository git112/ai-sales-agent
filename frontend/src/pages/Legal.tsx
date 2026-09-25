import { Link } from "react-router-dom";
import { ArrowLeft, ShieldCheck } from "lucide-react";

export default function Legal({ kind }: { kind: "privacy" | "terms" }) {
  return (
    <div className="min-h-screen bg-slate-50/50 py-12 px-6">
      <div className="max-w-3xl mx-auto space-y-6">
        <div className="flex items-center justify-between pb-4 border-b border-slate-200">
          <Link to="/" className="flex items-center gap-2.5">
            <span className="logo-mark">L</span>
            <span className="font-bold text-slate-900 font-display text-lg">Lumina</span>
          </Link>
          <Link to="/" className="btn btn-ghost text-xs py-2 px-3 flex items-center gap-1.5">
            <ArrowLeft className="w-3.5 h-3.5" />
            Back Home
          </Link>
        </div>

        <div className="card p-8 bg-white shadow-xs space-y-4">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-indigo-50 text-indigo-600 border border-indigo-100">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <h1 className="text-3xl font-bold font-display text-slate-900 tracking-tight">
              {kind === "privacy" ? "Privacy Policy" : "Terms of Service"}
            </h1>
          </div>
          <p className="text-slate-600 text-sm leading-relaxed pt-2">
            Lumina Autonomous Sales Agent processes public buying signals and opportunity leads in accordance with enterprise data protection standards.
            Discovered records adhere to privacy boundaries, compliance opt-out registries, and explicit consent handling.
            Do-not-contact requests are enforced across all campaign execution and calling queues.
          </p>
          <p className="text-slate-600 text-sm leading-relaxed">
            All AI-generated voice qualification conversations comply with jurisdiction-specific recording disclosure guidelines and telecommunication regulations.
          </p>
        </div>
      </div>
    </div>
  );
}
