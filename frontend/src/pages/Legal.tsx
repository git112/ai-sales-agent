import { Link } from "react-router-dom";

export default function Legal({ kind }: { kind: "privacy" | "terms" }) {
  return (
    <div className="min-h-screen">
      <div className="max-w-3xl mx-auto px-6 py-16">
        <div className="flex justify-between">
          <Link to="/" className="text-sm text-blue-800">
            Back
          </Link>
        </div>
        <h1 className="text-3xl font-semibold mt-4">{kind === "privacy" ? "Privacy Policy" : "Terms of Service"}</h1>
        <p className="text-slate-600 mt-4 text-sm leading-6">
          Lumina Autonomous Sales Agent processes public buying signals and opportunity leads in accordance with enterprise data protection standards.
          Discovered records adhere to privacy boundaries, compliance opt-out registries, and explicit consent handling.
          Do-not-contact requests are enforced across all campaign execution and calling queues.
        </p>
      </div>
    </div>
  );
}
