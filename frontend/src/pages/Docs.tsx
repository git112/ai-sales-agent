import { Link } from "react-router-dom";

export default function Docs() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-12 space-y-6">
      <h1 className="font-display text-4xl">Platform Documentation</h1>
      <p className="text-slate-500">System architecture, intelligence engine, and workflow documentation.</p>
      {[
        ["Product overview", "Lumina turns a business profile into opportunity discovery, explainable scoring, automated voice qualification, and actionable follow-up."],
        ["AI discovery", "Natural-language search queries verified enterprise data sources and public market catalogs. Live fetch is verified and source-attributed."],
        ["Lead enrichment", "Company, website, industry, size, location, and technology come from structured verified records with source confidence and timestamp."],
        ["Voice Agent Studio", "Multilingual conversational engine supporting English, Hindi, and Gujarati scripts with natural turn-taking and qualification logic."],
        ["Campaign workflow", "Launch, pause, resume, and step execution. Automated retry sequences with customizable quiet hours and policies."],
        ["Opportunity DNA", "Structured requirements, technology stack, location, why-match rationale, urgency triggers, risks, and missing data."],
        ["Why Match / Why Now", "Explainable AI heuristic scoring bound to traceable market evidence quotes."],
        ["Next Best Action", "Autonomous recommendations based on prospect interest level: meeting scheduling, callback tasks, or research escalation."],
        ["API Architecture", "RESTful API under /api/v1 with JWT authentication, tenant workspace isolation, and rate-limiting."],
        ["Security & Compliance", "Encrypted credentials, tenant boundary enforcement, automated opt-out registry, and audit trails."],
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
