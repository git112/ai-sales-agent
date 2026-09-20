import { Link } from "react-router-dom";

export default function Docs() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-12 space-y-6">
      <h1 className="font-display text-4xl">Documentation</h1>
      <p className="text-gray-500">Hackathon MVP overview — not a full developer portal.</p>
      {[
        ["Product overview", "Lumina turns a business profile into opportunity discovery, explainable scoring, demo voice qualification, and human follow-up."],
        ["AI discovery", "Natural-language search hits Demo Source JSON plus a Public Web catalog. Live fetch is optional and labeled. Nothing is invented."],
        ["Lead enrichment", "Company, website, industry, size, location, and technology come from stored records with source, confidence, and last updated."],
        ["Demo Voice", "Simulation only. English, Hindi, and Gujarati scripts. No browser speech recognition or live telephony."],
        ["Campaign workflow", "Launch, pause, resume, then Run next campaign step. Retry sequence is deterministic: No Answer → Voicemail → Connected/Interested."],
        ["Opportunity DNA", "Structured requirement, technology, location, why match, why now, risks, and missing fields."],
        ["Why Match / Why Now", "Heuristic explanations bound to evidence quotes. Insufficient evidence is stated, not filled."],
        ["Next Best Action", "Derived from qualification interest: meeting, callback, stop, or research."],
        ["Demo vs Live", "DEMO MODE uses JSON and simulated calls. LIVE MODE uses the same JSON; telephony stays blocked until providers exist."],
        ["API overview", "REST under /api/v1. JWT auth. Workspace via X-Workspace-Id. JSON store, no SQL."],
        ["Security basics", "Passwords hashed. Tenant isolation for non-admins. Opt-out list. Rate limit. Secrets stay in .env."],
      ].map(([t, b]) => (
        <section key={t} className="card p-5">
          <h2 className="font-semibold">{t}</h2>
          <p className="text-sm text-gray-600 mt-2">{b}</p>
        </section>
      ))}
      <Link className="text-blue-800 text-sm" to="/">
        Back home
      </Link>
    </div>
  );
}
