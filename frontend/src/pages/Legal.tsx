import { Link } from "react-router-dom";
import ThemeToggle from "../ThemeToggle";

export default function Legal({ kind }: { kind: "privacy" | "terms" }) {
  return (
    <div className="min-h-screen">
      <div className="max-w-3xl mx-auto px-6 py-16">
        <div className="flex justify-between">
          <Link to="/" className="text-sm text-blue-800">
            Back
          </Link>
          <ThemeToggle />
        </div>
        <h1 className="text-3xl font-semibold mt-4">{kind === "privacy" ? "Privacy" : "Terms"}</h1>
        <p className="text-gray-600 mt-4 text-sm leading-6">
          Lumina is a hackathon MVP. Demo records are synthetic and labeled DEMO DATA. Contact details in the seed set are
          example.com placeholders. Discovery uses demo adapters unless a permitted public source is configured. Do-not-contact
          requests are stored in the workspace opt-out list.
        </p>
      </div>
    </div>
  );
}
