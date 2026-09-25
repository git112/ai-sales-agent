import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Compass, Sparkles, CheckCircle2, ArrowRight, ArrowLeft, Globe } from "lucide-react";
import { api } from "../api";

export default function Onboarding() {
  const nav = useNavigate();
  const [step, setStep] = useState(1);
  const [form, setForm] = useState({
    company_name: "Nexus Cloud Systems",
    website: "https://nexuscloud.io",
    description: "Enterprise cloud infrastructure, AI-driven automation, and hybrid multi-cloud solutions for Fortune 500 and high-growth technology companies.",
    industry: "Cloud Infrastructure & AI",
    location: "San Francisco, CA",
    services: "Cloud Migration, Infrastructure Automation, AI Platform Deployment, DevSecOps",
    products: "Nexus Orbit Platform, CloudSync AI, SecureEdge Gateway",
    technologies: "Kubernetes, Terraform, AWS, Azure, GCP, Python, Go",
    target_industries: "Technology, Financial Services, Healthcare, Retail",
    target_locations: "USA, UK, Singapore, UAE",
    company_size: "501-2000",
    target_roles: "CTO, VP Engineering, Head of Cloud, DevOps Director",
    keywords: "cloud migration, infrastructure automation, AI deployment",
  });
  const [profile, setProfile] = useState<any>(null);
  const [msg, setMsg] = useState("");
  const [urlErr, setUrlErr] = useState("");
  const [urlState, setUrlState] = useState<"idle" | "loading" | "success" | "error">("idle");

  const set = (k: string, v: string) => setForm({ ...form, [k]: v });
  const split = (s: string) => s.split(",").map((x) => x.trim()).filter(Boolean);

  function validUrl(u: string) {
    try {
      const parsed = new URL(u.startsWith("http") ? u : `https://${u}`);
      return parsed.protocol === "https:" || parsed.hostname === "localhost";
    } catch {
      return false;
    }
  }

  async function analyzeWebsite() {
    setUrlErr("");
    if (!validUrl(form.website)) {
      setUrlErr("Enter a valid https URL.");
      setUrlState("error");
      return;
    }
    setUrlState("loading");
    try {
      const { data } = await api.post("/business-profile/analyze-url", { url: form.website });
      setProfile(data);
      setMsg(data.fetch_status === "ok" ? "Extracted from the public page, then structured." : "Live fetch failed. Showing labeled fallback — nothing invented as live.");
      setUrlState(data.fetch_status === "failed" && data.label === "Not detected" ? "error" : "success");
      setStep(5);
    } catch (e: any) {
      setUrlErr(e.response?.data?.error?.message || "Could not analyze URL.");
      setUrlState("error");
    }
  }

  async function analyze() {
    const payload = {
      ...form,
      services: split(form.services),
      products: split(form.products),
      technologies: split(form.technologies),
      target_industries: split(form.target_industries),
      target_locations: split(form.target_locations),
      target_roles: split(form.target_roles),
      keywords: split(form.keywords),
    };
    const { data } = await api.post("/onboarding", payload);
    setProfile(data.profile);
    setMsg(data.message);
    setStep(5);
  }

  return (
    <div className="max-w-3xl space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-indigo-50 text-indigo-600 border border-indigo-100">
            <Compass className="w-5 h-5" />
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight font-display">AI-Powered Business Setup</h1>
        </div>
        <p className="text-sm text-slate-500 mt-1">
          Configure your company profile and let the AI structure your go-to-market intelligence. Approve the profile before activating discovery.
        </p>
      </div>

      <div className="flex gap-2 text-xs flex-wrap">
        {[
          { n: 1, label: "Company" },
          { n: 2, label: "Products" },
          { n: 3, label: "Targets" },
          { n: 4, label: "Knowledge" },
          { n: 5, label: "AI Review" },
        ].map(({ n, label }) => (
          <span
            key={n}
            className={`px-3.5 py-1.5 rounded-full text-xs font-semibold transition-all ${
              step === n
                ? "bg-indigo-600 text-white shadow-xs"
                : "bg-white border border-slate-200 text-slate-600"
            }`}
          >
            {label}
          </span>
        ))}
      </div>

      {step === 1 && (
        <div className="card p-6 mt-6 space-y-3">
          <h2 className="font-semibold">Company information</h2>
          {["company_name", "website", "description", "industry", "location"].map((k) => (
            <input key={k} className="input" value={(form as any)[k]} onChange={(e) => set(k, e.target.value)} placeholder={k.replace("_", " ")} />
          ))}
          {urlErr && <p className="text-sm text-red-600">{urlErr}</p>}
          <button className="btn btn-ghost" disabled={urlState === "loading"} onClick={analyzeWebsite}>
            {urlState === "loading" ? "Analyzing website…" : "Analyze website"}
          </button>
          {urlState === "success" && <p className="text-sm text-green-700">Website analysis ready.</p>}
          <button className="btn btn-primary ml-2" onClick={() => setStep(2)}>
            Continue
          </button>
        </div>
      )}
      {step === 2 && (
        <div className="card p-6 mt-6 space-y-3">
          <h2 className="font-semibold">Products / services</h2>
          <input className="input" value={form.products} onChange={(e) => set("products", e.target.value)} placeholder="Products" />
          <input className="input" value={form.services} onChange={(e) => set("services", e.target.value)} placeholder="Services" />
          <input className="input" value={form.technologies} onChange={(e) => set("technologies", e.target.value)} placeholder="Technologies" />
          <button className="btn btn-ghost" onClick={() => setStep(1)}>
            Back
          </button>
          <button className="btn btn-primary ml-2" onClick={() => setStep(3)}>
            Continue
          </button>
        </div>
      )}
      {step === 3 && (
        <div className="card p-6 mt-6 space-y-3">
          <h2 className="font-semibold">Target customers</h2>
          <input className="input" value={form.target_industries} onChange={(e) => set("target_industries", e.target.value)} />
          <input className="input" value={form.target_locations} onChange={(e) => set("target_locations", e.target.value)} />
          <input className="input" value={form.company_size} onChange={(e) => set("company_size", e.target.value)} />
          <input className="input" value={form.target_roles} onChange={(e) => set("target_roles", e.target.value)} />
          <input className="input" value={form.keywords} onChange={(e) => set("keywords", e.target.value)} />
          <button className="btn btn-ghost" onClick={() => setStep(2)}>
            Back
          </button>
          <button className="btn btn-primary ml-2" onClick={() => setStep(4)}>
            Continue
          </button>
        </div>
      )}
      {step === 4 && (
        <div className="card p-6 mt-6 space-y-3">
          <h2 className="font-semibold">Knowledge</h2>
          <p className="text-sm text-gray-600">Upload PDF, DOCX, or TXT in Knowledge Base, or analyze the form plus website.</p>
          <button className="btn btn-ghost" onClick={() => setStep(3)}>
            Back
          </button>
          <button className="btn btn-ghost ml-2" disabled={urlState === "loading"} onClick={analyzeWebsite}>
            {urlState === "loading" ? "Analyzing…" : "Analyze website"}
          </button>
          <button className="btn btn-primary ml-2" onClick={analyze}>
            Analyze with AI
          </button>
        </div>
      )}
      {step === 5 && profile && (
        <div className="card p-6 mt-6 space-y-3">
          <h2 className="font-semibold">{msg || "AI has structured your business intelligence profile."}</h2>
          {profile.confidence && (
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-gray-500">AI Confidence:</span>
              <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                profile.confidence >= 0.8 ? "bg-emerald-100 text-emerald-700" :
                profile.confidence >= 0.5 ? "bg-amber-100 text-amber-700" :
                "bg-slate-100 text-slate-600"
              }`}>
                {Math.round((profile.confidence || 0) * 100)}% match
              </span>
            </div>
          )}
          {profile.fetch_error && (
            <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-3 py-1.5">
              ⚠ {profile.fetch_error} — Profile built from form data.
            </p>
          )}
          <textarea className="input h-28" value={profile.company_summary || ""} onChange={(e) => setProfile({ ...profile, company_summary: e.target.value })} />
          <p className="text-sm">
            <strong>Services:</strong> {(profile.services || profile.products_services || []).join(", ") || "—"}
          </p>
          <p className="text-sm">
            <strong>Technologies:</strong> {(profile.technologies || []).join(", ") || "—"}
          </p>
          <p className="text-sm">
            <strong>Pain points:</strong> {(profile.likely_pain_points || []).join("; ") || "—"}
          </p>
          <p className="text-sm">
            <strong>Buying signals:</strong> {(profile.buying_signals || profile.likely_buying_signals || []).join("; ") || "—"}
          </p>
          <button
            className="btn btn-primary"
            onClick={async () => {
              await api.post("/business-profile/approve", profile);
              nav("/app/opportunities");
            }}
          >
            Approve profile
          </button>
        </div>
      )}
    </div>
  );
}
