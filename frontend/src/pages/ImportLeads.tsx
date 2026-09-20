import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";

export default function ImportLeads() {
  const nav = useNavigate();
  const [preview, setPreview] = useState<any>(null);
  const [mapping, setMapping] = useState<any>({});
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-semibold">CSV / Excel import</h1>
      <p className="text-sm text-gray-500">Preview, map columns, validate, detect duplicates, then import valid rows only.</p>
      <input
        className="mt-4"
        type="file"
        accept=".csv,.xlsx"
        onChange={async (e) => {
          const file = e.target.files?.[0];
          if (!file) return;
          const fd = new FormData();
          fd.append("file", file);
          const { data } = await api.post("/leads/import/preview", fd);
          setPreview(data);
          setMapping(data.mapping);
        }}
      />
      {preview && (
        <div className="card p-4 mt-4 space-y-3">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
            <div>Total: {preview.total_rows ?? preview.count}</div>
            <div>Valid: {preview.valid_rows}</div>
            <div>Invalid: {preview.invalid_rows}</div>
            <div>Duplicates: {preview.duplicate_rows}</div>
          </div>
          {Object.keys(mapping).map((f) => (
            <label key={f} className="flex gap-2 text-sm items-center">
              <span className="w-32">{f}</span>
              <select className="input" value={mapping[f] || ""} onChange={(e) => setMapping({ ...mapping, [f]: e.target.value })}>
                <option value="">—</option>
                {preview.headers.map((h: string) => (
                  <option key={h}>{h}</option>
                ))}
              </select>
            </label>
          ))}
          {(preview.errors || []).length > 0 && (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500">
                  <th>Row</th>
                  <th>Field</th>
                  <th>Problem</th>
                  <th>Suggested correction</th>
                </tr>
              </thead>
              <tbody>
                {preview.errors.map((e: any, i: number) => (
                  <tr key={i}>
                    <td>{e.row}</td>
                    <td>{e.field}</td>
                    <td>{e.problem}</td>
                    <td>{e.suggested}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {err && <p className="text-sm text-red-600">{err}</p>}
          <div className="flex gap-2">
            <button
              className="btn btn-primary"
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                setErr("");
                try {
                  await api.post("/leads/import", { mapping, rows: (preview.preview || []).map((p: any) => p.row) });
                  nav("/app/leads");
                } catch (e: any) {
                  setErr(e.response?.data?.error?.message || "Import failed");
                } finally {
                  setBusy(false);
                }
              }}
            >
              {busy ? "Importing…" : "Continue with valid rows"}
            </button>
            <button className="btn btn-ghost" onClick={() => nav("/app/leads")}>
              Cancel import
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
