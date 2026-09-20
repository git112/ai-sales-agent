import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";

export default function Onboarding() {
  const nav = useNavigate();
  const [step, setStep] = useState(1);
  const [form, setForm] = useState({
    company_name: "Northwind Digital",
    website: "https://example.com/northwind-digital",
    description: "Microsoft 365 and SharePoint consulting: implementation, migration, integration, custom development, enterprise document management.",
    industry: "IT consulting",
    location: "Ahmedabad, India",
    services: "SharePoint implementation, SharePoint migration, Microsoft 365 consulting",
    products: "Delivery accelerators",
    technologies: "SharePoint, Microsoft 365",
    target_industries: "Technology, Manufacturing, BFSI",
    target_locations: "India, UAE",
    company_size: "201-500",
    target_roles: "CIO, IT Director, SharePoint Admin",
    keywords: "SharePoint implementation, migration",
  });
  const [profile, setProfile] = useState<any>(null);
  const [msg, setMsg] = useState("");

  const set = (k: string, v: string) => setForm({ ...form, [k]: v });
  const split = (s: string) => s.split(",").map((x) => x.trim()).filter(Boolean);

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
    <div className="max-w-3xl">
      <h1 className="text-2xl font-semibold">AI-powered setup</h1>
      <p className="text-gray-500 text-sm mt-1">Four steps, then structured business understanding you can approve or edit.</p>
      <div className="flex gap-2 mt-4 text-xs">
        {[1, 2, 3, 4, 5].map((n) => (
          <span key={n} className={`px-2 py-1 rounded ${step === n ? "bg-blue-700 text-white" : "bg-gray-200"}`}>
            {n < 5 ? `Step ${n}` : "AI"}
          </span>
        ))}
      </div>

      {step === 1 && (
        <div className="card p-6 mt-6 space-y-3">
          <h2 className="font-semibold">Company information</h2>
          {["company_name", "website", "description", "industry", "location"].map((k) => (
            <input key={k} className="input" value={(form as any)[k]} onChange={(e) => set(k, e.target.value)} placeholder={k} />
          ))}
          <button className="btn btn-primary" onClick={() => setStep(2)}>
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
          <p className="text-sm text-gray-600">Upload PDF, DOCX, or TXT in Knowledge Base. You can also continue with the description above.</p>
          <button className="btn btn-ghost" onClick={() => setStep(3)}>
            Back
          </button>
          <button className="btn btn-primary ml-2" onClick={analyze}>
            Analyze with AI
          </button>
        </div>
      )}
      {step === 5 && profile && (
        <div className="card p-6 mt-6 space-y-3">
          <h2 className="font-semibold">{msg || "Here's what AI understood about your business."}</h2>
          <textarea className="input h-28" value={profile.company_summary} onChange={(e) => setProfile({ ...profile, company_summary: e.target.value })} />
          <p className="text-sm">
            <strong>Services:</strong> {(profile.services || []).join(", ")}
          </p>
          <p className="text-sm">
            <strong>Technologies:</strong> {(profile.technologies || []).join(", ")}
          </p>
          <p className="text-sm">
            <strong>Buying signals:</strong> {(profile.buying_signals || []).join("; ")}
          </p>
          <p className="text-xs text-gray-500">
            Source: {profile.source} · Confidence {profile.confidence} · AI never fabricates missing fields.
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
