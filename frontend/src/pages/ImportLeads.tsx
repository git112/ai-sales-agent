import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";

export default function ImportLeads() {
  const nav = useNavigate();
  const [preview, setPreview] = useState<any>(null);
  const [mapping, setMapping] = useState<any>({});

  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-semibold">CSV / Excel import</h1>
      <p className="text-sm text-gray-500">Preview, map columns, validate, detect duplicates, then import.</p>
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
          <p className="text-sm">{preview.count} rows. Duplicates flagged in preview.</p>
          <button
            className="btn btn-primary"
            onClick={async () => {
              const rows = preview.preview.filter((p: any) => p.valid && !p.duplicate).map((p: any) => p.row);
              await api.post("/leads/import", { mapping, rows });
              nav("/app/leads");
            }}
          >
            Import valid unique rows
          </button>
        </div>
      )}
    </div>
  );
}
