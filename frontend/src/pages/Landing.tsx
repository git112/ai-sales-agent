import { Link } from "react-router-dom";
import { Sparkles, ArrowRight, CheckCircle2 } from "lucide-react";

const steps = ["Discover", "Understand", "Prioritize", "Enrich", "Call", "Qualify", "Follow Up"];

export default function Landing() {
  return (
    <div className="min-h-screen bg-slate-50/50">
      <header className="max-w-6xl mx-auto px-6 py-5 flex items-center justify-between">
        <Link to="/" className="font-bold tracking-tight flex items-center gap-2.5 text-lg font-display text-slate-900">
          <span className="logo-mark">L</span>
          Lumina
        </Link>
        <div className="flex items-center gap-3">
          <nav className="hidden md:flex gap-6 text-sm font-medium text-slate-600 items-center">
            <a href="#how" className="hover:text-indigo-600 transition">How it works</a>
            <a href="#features" className="hover:text-indigo-600 transition">Features</a>
            <Link to="/docs" className="hover:text-indigo-600 transition">Docs</Link>
            <Link to="/pricing" className="hover:text-indigo-600 transition">Pricing</Link>
            <Link to="/login" className="btn btn-ghost text-xs py-2 px-3.5">
              Sign In
            </Link>
            <Link to="/signup" className="btn btn-primary text-xs py-2 px-3.5">
              Get Started
            </Link>
          </nav>
        </div>
      </header>

      <section className="max-w-6xl mx-auto px-6 py-16 grid lg:grid-cols-2 gap-12 items-center">
        <div>
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-200/70 text-indigo-700 text-xs font-semibold tracking-wider uppercase mb-4">
            <Sparkles className="w-3.5 h-3.5" />
            AI Sales Intelligence Platform
          </div>
          <h1 className="font-display text-5xl leading-[1.12] font-bold text-slate-900 tracking-tight">
            From buying signals to <span className="text-indigo-600">qualified</span> sales opportunities.
          </h1>
          <p className="mt-5 text-slate-600 text-lg max-w-xl leading-relaxed">
            Lumina understands what you sell, finds public buying signals, explains why they match and why now, then qualifies
            prospects with an AI voice agent — so a human can close.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/signup" className="btn btn-primary h-11 px-6 text-sm font-semibold">
              Get Started Free
            </Link>
            <Link to="/login" className="btn btn-ghost h-11 px-6 text-sm font-semibold">
              Sign In
            </Link>
          </div>
        </div>

        <div className="scene-3d">
          <div className="layer-3d back card p-5 bg-white shadow-xs">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Market Signal</div>
            <div className="mt-1.5 font-bold text-slate-800">Hiring SharePoint Administrator</div>
          </div>
          <div className="layer-3d mid card p-5 bg-white shadow-xs">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Why Now Trigger</div>
            <div className="mt-1.5 font-bold text-slate-800">Migration requirement posted this week</div>
          </div>
          <div className="layer-3d front card p-6 bg-white shadow-md tilt-3d border-indigo-200/60">
            <div className="text-xs font-bold tracking-[0.16em] text-indigo-600 mb-4">AUTONOMOUS WORKFLOW</div>
            <div className="flex flex-wrap gap-2">
              {steps.map((s, i) => (
                <span key={s} className="flex items-center gap-2">
                  <span className="bg-indigo-50 text-indigo-700 border border-indigo-100 px-3 py-1 rounded-full text-xs font-semibold">{s}</span>
                  {i < steps.length - 1 && <span className="text-slate-300 text-xs">→</span>}
                </span>
              ))}
            </div>
            <div className="mt-6 grid grid-cols-3 gap-3 text-center">
              {[
                ["91", "AI score"],
                ["Why now", "Evidence"],
                ["HIGH", "Intent"],
              ].map(([a, b]) => (
                <div key={b} className="rounded-xl border border-slate-200/80 bg-slate-50/50 py-3">
                  <div className="text-2xl font-bold font-display text-indigo-600">{a}</div>
                  <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mt-1">{b}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="py-16" id="how">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-3xl font-bold font-display text-slate-900 tracking-tight">The Problem</h2>
          <p className="mt-3 text-slate-600 max-w-3xl leading-relaxed">
            Sales teams hunt requirements across the public web, cannot explain why an opportunity matters now, and spend hours on
            unqualified calls. Lumina centralizes discovery, evidence, and qualification.
          </p>
          <h3 className="mt-12 text-2xl font-bold font-display text-slate-900 tracking-tight">How It Works</h3>
          <ol className="mt-6 grid md:grid-cols-4 gap-4">
            {["Give us your business", "AI finds buying signals", "AI explains match and timing", "AI qualifies; humans close"].map(
              (x, i) => (
                <li key={x} className="card p-5 bg-white shadow-xs tilt-3d border-slate-200">
                  <div className="text-xs text-indigo-600 font-bold tracking-widest uppercase">STEP {i + 1}</div>
                  <div className="mt-3 font-semibold text-base text-slate-800">{x}</div>
                </li>
              )
            )}
          </ol>
        </div>
      </section>

      <section className="py-16 max-w-6xl mx-auto px-6" id="features">
        <h2 className="text-3xl font-bold font-display text-slate-900 tracking-tight">AI Sales Workflow</h2>
        <p className="text-slate-600 mt-2">Business understanding → discovery → Opportunity DNA → voice qualification → next-best action.</p>
        <div className="grid md:grid-cols-3 gap-4 mt-8">
          {[
            ["Opportunity Intelligence", "AI Opportunity Score, Why Match, Why Now, evidence, and Opportunity DNA."],
            ["AI Voice Agent", "Autonomous voice qualification with disclosure, opt-out, handoff, live transcripts, and interest detection."],
            ["Executive Analytics", "Calls, qualification outcomes, campaign performance, and an AI copilot grounded in workspace data."],
          ].map(([h, b]) => (
            <div key={h} className="card p-6 bg-white shadow-xs tilt-3d">
              <h3 className="font-display text-xl font-bold text-slate-900">{h}</h3>
              <p className="text-sm text-slate-600 mt-2.5 leading-relaxed">{b}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="py-16 max-w-6xl mx-auto px-6">
        <div className="card p-12 bg-white shadow-md text-center border-indigo-100">
          <h2 className="text-3xl font-bold font-display text-slate-900">Ready to illuminate the signal?</h2>
          <p className="text-slate-600 mt-3 max-w-xl mx-auto">See your business go from verified market signals to qualified high-intent meetings autonomously.</p>
          <Link to="/signup" className="btn btn-primary mt-6 px-8 py-3 text-sm font-semibold">
            Create Free Workspace
          </Link>
        </div>
      </section>

      <footer className="border-t border-slate-200 py-8 text-sm text-slate-500 bg-white">
        <div className="max-w-6xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="logo-mark !w-6 !h-6 !text-xs !mr-0">L</span>
            <span className="font-bold text-slate-800">Lumina</span>
            <span className="text-slate-400">· Autonomous Sales Intelligence</span>
          </div>
          <div className="flex gap-5 font-medium text-xs">
            <Link to="/privacy" className="hover:text-indigo-600 transition">Privacy</Link>
            <Link to="/terms" className="hover:text-indigo-600 transition">Terms</Link>
            <Link to="/pricing" className="hover:text-indigo-600 transition">Pricing</Link>
            <Link to="/docs" className="hover:text-indigo-600 transition">Docs</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
