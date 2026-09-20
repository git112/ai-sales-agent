import { Link } from "react-router-dom";
import ThemeToggle from "../ThemeToggle";

const steps = ["Discover", "Understand", "Prioritize", "Enrich", "Call", "Qualify", "Follow Up"];

export default function Landing() {
  return (
    <div className="min-h-screen">
      <header className="max-w-6xl mx-auto px-6 py-5 flex items-center justify-between">
        <div className="font-semibold tracking-tight flex items-center text-lg">
          <span className="logo-mark">L</span>
          Lumina
        </div>
        <div className="flex items-center gap-3">
          <ThemeToggle />
          <nav className="hidden md:flex gap-5 text-sm text-gray-500 items-center">
            <a href="#how">How it works</a>
            <a href="#features">Features</a>
            <Link to="/pricing">Pricing</Link>
            <Link to="/login" className="btn btn-ghost">
              Login
            </Link>
            <Link to="/signup" className="btn btn-primary">
              Start demo
            </Link>
          </nav>
        </div>
      </header>

      <section className="max-w-6xl mx-auto px-6 py-16 grid lg:grid-cols-2 gap-12 items-center">
        <div>
          <p className="text-sm font-semibold tracking-[0.18em] uppercase accent mb-4">AI sales intelligence</p>
          <h1 className="font-display text-5xl leading-[1.12] font-medium">
            From buying signals to <span className="accent">qualified</span> sales opportunities.
          </h1>
          <p className="mt-5 text-gray-500 text-lg max-w-xl">
            Lumina understands what you sell, finds public buying signals, explains why they match and why now, then qualifies
            prospects with an AI voice agent — so a human can close.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/signup" className="btn btn-primary">
              Get started
            </Link>
            <Link to="/login" className="btn btn-ghost">
              Demo login
            </Link>
          </div>
        </div>

        <div className="scene-3d">
          <div className="layer-3d back card p-5">
            <div className="text-xs text-gray-500">Market signal</div>
            <div className="mt-2 font-medium">Hiring SharePoint admin</div>
          </div>
          <div className="layer-3d mid card p-5">
            <div className="text-xs text-gray-500">Why now</div>
            <div className="mt-2 font-medium">Requirement posted this week</div>
          </div>
          <div className="layer-3d front card p-6 score-glow tilt-3d">
            <div className="text-xs font-semibold tracking-[0.16em] accent mb-4">WORKFLOW</div>
            <div className="flex flex-wrap gap-2">
              {steps.map((s, i) => (
                <span key={s} className="flex items-center gap-2">
                  <span className="bg-blue-50 text-blue-800 px-3 py-1.5 rounded-full text-sm font-medium">{s}</span>
                  {i < steps.length - 1 && <span className="text-gray-500">→</span>}
                </span>
              ))}
            </div>
            <div className="mt-6 grid grid-cols-3 gap-3 text-center">
              {[
                ["91", "AI score"],
                ["Why now", "Evidence"],
                ["HIGH", "Intent"],
              ].map(([a, b]) => (
                <div key={b} className="rounded-xl border py-3" style={{ borderColor: "var(--line)" }}>
                  <div className="text-xl font-display accent">{a}</div>
                  <div className="text-[11px] text-gray-500 mt-1">{b}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="py-16" id="how">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-3xl">The problem</h2>
          <p className="mt-3 text-gray-500 max-w-3xl">
            Sales teams hunt requirements across the public web, cannot explain why an opportunity matters now, and spend hours on
            unqualified calls. Lumina centralizes discovery, evidence, and qualification.
          </p>
          <h3 className="mt-12 text-2xl">How it works</h3>
          <ol className="mt-6 grid md:grid-cols-4 gap-4">
            {["Give us your business", "AI finds buying signals", "AI explains match and timing", "AI qualifies; humans close"].map(
              (x, i) => (
                <li key={x} className="card p-5 tilt-3d">
                  <div className="text-xs accent font-semibold tracking-widest">STEP {i + 1}</div>
                  <div className="mt-3 font-medium text-lg">{x}</div>
                </li>
              )
            )}
          </ol>
        </div>
      </section>

      <section className="py-16 max-w-6xl mx-auto px-6" id="features">
        <h2 className="text-3xl">AI workflow</h2>
        <p className="text-gray-500 mt-2">Business understanding → discovery → Opportunity DNA → voice qualification → next-best action.</p>
        <div className="grid md:grid-cols-3 gap-4 mt-8">
          {[
            ["Opportunity Intelligence", "AI Opportunity Score, Why Match, Why Now, evidence, and Opportunity DNA."],
            ["AI Voice Agent", "Demo voice simulation with disclosure, opt-out, handoff, transcripts, and interest detection."],
            ["Analytics", "Calls, qualification outcomes, campaign performance, and an AI copilot grounded in workspace data."],
          ].map(([h, b]) => (
            <div key={h} className="card p-6 tilt-3d">
              <h3 className="font-display text-xl">{h}</h3>
              <p className="text-sm text-gray-500 mt-3 leading-relaxed">{b}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="py-20">
        <div className="max-w-6xl mx-auto px-6 text-center card py-14">
          <h2 className="text-3xl">Ready to illuminate the signal?</h2>
          <p className="text-gray-500 mt-3">See ABC Technologies go from a SharePoint requirement to a high-intent follow-up.</p>
          <Link to="/signup" className="btn btn-primary mt-7">
            Create workspace
          </Link>
        </div>
      </section>

      <footer className="border-t py-8 text-sm text-gray-500">
        <div className="max-w-6xl mx-auto px-6 flex justify-between">
          <span>Lumina · Hackathon MVP</span>
          <div className="flex gap-4">
            <Link to="/privacy">Privacy</Link>
            <Link to="/terms">Terms</Link>
            <Link to="/pricing">Pricing</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
