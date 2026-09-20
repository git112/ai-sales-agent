import { Link } from "react-router-dom";

const steps = ["Discover", "Understand", "Prioritize", "Enrich", "Call", "Qualify", "Follow Up"];

export default function Landing() {
  return (
    <div className="bg-white text-gray-900">
      <header className="max-w-6xl mx-auto px-6 py-5 flex items-center justify-between">
        <div className="font-semibold text-[#1e3a8a]">Lumina</div>
        <nav className="flex gap-5 text-sm text-gray-600">
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
      </header>

      <section className="max-w-6xl mx-auto px-6 py-20 grid md:grid-cols-2 gap-12 items-center">
        <div>
          <p className="text-sm font-semibold text-blue-700 mb-3">AI sales intelligence</p>
          <h1 className="text-4xl font-semibold leading-tight text-gray-900">From buying signals to qualified sales opportunities.</h1>
          <p className="mt-4 text-gray-600 text-lg">
            Lumina understands what you sell, finds public buying signals, explains why they match and why now, then qualifies
            prospects with an AI voice agent — so a human can close.
          </p>
          <div className="mt-8 flex gap-3">
            <Link to="/signup" className="btn btn-primary">
              Get started
            </Link>
            <Link to="/login" className="btn btn-ghost">
              Demo login
            </Link>
          </div>
        </div>
        <div className="card p-6">
          <div className="text-xs font-semibold text-gray-500 mb-4">WORKFLOW</div>
          <div className="flex flex-wrap gap-2">
            {steps.map((s, i) => (
              <span key={s} className="flex items-center gap-2">
                <span className="bg-blue-50 text-blue-800 px-3 py-1 rounded-full text-sm font-medium">{s}</span>
                {i < steps.length - 1 && <span className="text-gray-300">→</span>}
              </span>
            ))}
          </div>
          <p className="mt-6 text-sm text-gray-500">Hackathon MVP. Demo data is always labeled. No unauthorized scraping.</p>
        </div>
      </section>

      <section className="bg-[#f4f6f8] py-16" id="how">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-2xl font-semibold">The problem</h2>
          <p className="mt-3 text-gray-600 max-w-3xl">
            Sales teams hunt requirements across the public web, cannot explain why an opportunity matters now, and spend hours on
            unqualified calls. Lumina centralizes discovery, evidence, and qualification.
          </p>
          <h3 className="mt-10 text-xl font-semibold">How it works</h3>
          <ol className="mt-4 grid md:grid-cols-4 gap-4">
            {["Give us your business", "AI finds buying signals", "AI explains match and timing", "AI qualifies; humans close"].map(
              (x, i) => (
                <li key={x} className="card p-4">
                  <div className="text-xs text-blue-700 font-semibold">STEP {i + 1}</div>
                  <div className="mt-2 font-medium">{x}</div>
                </li>
              )
            )}
          </ol>
        </div>
      </section>

      <section className="py-16 max-w-6xl mx-auto px-6" id="features">
        <h2 className="text-2xl font-semibold">AI workflow</h2>
        <p className="text-gray-600 mt-2">Business understanding → discovery → Opportunity DNA → voice qualification → next-best action.</p>
        <div className="grid md:grid-cols-3 gap-4 mt-8">
          {[
            ["Opportunity Intelligence", "AI Opportunity Score, Why Match, Why Now, evidence, and Opportunity DNA."],
            ["AI Voice Agent", "Demo voice simulation with disclosure, opt-out, handoff, transcripts, and interest detection."],
            ["Analytics", "Calls, qualification outcomes, campaign performance, and an AI copilot grounded in workspace data."],
          ].map(([h, b]) => (
            <div key={h} className="card p-5">
              <h3 className="font-semibold">{h}</h3>
              <p className="text-sm text-gray-600 mt-2">{b}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="bg-[#f4f6f8] py-16">
        <div className="max-w-6xl mx-auto px-6 text-center">
          <h2 className="text-2xl font-semibold">Ready to illuminate the signal?</h2>
          <Link to="/signup" className="btn btn-primary mt-6">
            Create workspace
          </Link>
        </div>
      </section>

      <footer className="border-t border-gray-200 py-8 text-sm text-gray-500">
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
