import { Link } from "react-router-dom";
import { BookOpen, ArrowLeft } from "lucide-react";

export default function Docs() {
  return (
    <div className="min-h-screen bg-slate-50/50 py-12 px-6">
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="flex items-center justify-between pb-4 border-b border-slate-200">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-indigo-50 text-indigo-600 border border-indigo-100">
              <BookOpen className="w-5 h-5" />
            </div>
            <div>
              <h1 className="font-display text-3xl font-bold text-slate-900 tracking-tight">Platform Documentation</h1>
              <p className="text-sm text-slate-500 mt-0.5">System architecture, intelligence engine, and workflow documentation.</p>
            </div>
          </div>
          <Link className="btn btn-ghost text-xs py-2 px-3 flex items-center gap-1.5" to="/">
            <ArrowLeft className="w-3.5 h-3.5" />
            Back Home
          </Link>
        </div>

        <div className="grid gap-3.5">
          {[
            ["Product Overview", "Lumina turns a business profile into opportunity discovery, explainable scoring, automated voice qualification, and actionable follow-up."],
            ["AI Discovery Engine", "Natural-language search queries verified enterprise data sources and public market catalogs. Live fetch is verified and source-attributed."],
            ["Lead Enrichment Pipeline", "Company, website, industry, size, location, and technology come from structured verified records with source confidence and timestamp."],
            ["Voice Agent Studio", "Multilingual conversational engine supporting English, Hindi, and Gujarati scripts with natural turn-taking and qualification logic."],
            ["Campaign Workflow Orchestration", "Launch, pause, resume, and step execution. Automated retry sequences with customizable quiet hours and policies."],
            ["Opportunity DNA Analysis", "Structured requirements, technology stack, location, why-match rationale, urgency triggers, risks, and missing data."],
            ["Why Match / Why Now Scoring", "Explainable AI heuristic scoring bound to traceable market evidence quotes and freshness triggers."],
            ["Next Best Action Engine", "Autonomous recommendations based on prospect interest level: meeting scheduling, callback tasks, or research escalation."],
            ["API Architecture", "RESTful API under /api/v1 with JWT authentication, tenant workspace isolation, and rate-limiting."],
            ["Security & Compliance Guardrails", "Encrypted credentials, tenant boundary enforcement, automated opt-out registry, and audit trails."],
          ].map(([t, b]) => (
            <section key={t} className="card p-5 bg-white shadow-xs hover:border-slate-300 transition">
              <h2 className="font-bold text-slate-900 text-base font-display">{t}</h2>
              <p className="text-sm text-slate-600 mt-1.5 leading-relaxed">{b}</p>
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}
