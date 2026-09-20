import { useEffect, useState } from "react";
import { api } from "../api";

const FIELDS = [
  ["industry", "Industry"],
  ["location", "Location"],
  ["company_size", "Company size"],
  ["technology", "Technology"],
  ["opportunity_score", "Opportunity score"],
  ["intent_level", "Intent level"],
  ["lead_source", "Lead source"],
  ["campaign", "Campaign"],
  ["qualification_status", "Qualification"],
  ["pipeline_stage", "Pipeline stage"],
];
const OPS = ["equals", "contains", "greater_than", "less_than", "in"];

export default function Segments() {
  const [rows, setRows] = useState<any[]>([]);
  const [name, setName] = useState("High Intent SharePoint Leads in India");
  const [type, setType] = useState("dynamic");
  const [filters, setFilters] = useState<any[]>([
    { field: "industry", op: "contains", value: "technology" },
    { field: "location", op: "contains", value: "India" },
    { field: "technology", op: "contains", value: "SharePoint" },
    { field: "intent_level", op: "contains", value: "interest" },
    { field: "opportunity_score", op: "greater_than", value: 70 },
  ]);
  const [preview, setPreview] = useState<any>(null);
  const [editId, setEditId] = useState<string | null>(null);
  const [err, setErr] = useState("");

  async function load() {
    setRows((await api.get("/segments")).data);
  }
  useEffect(() => {
    load();
  }, []);

  const body = { name, type, filters, lead_ids: type === "static" ? (preview?.leads || []).map((l: any) => l.id) : [], active: true };

  return (
    <div>
      <h1 className="text-2xl font-semibold">Lead segments</h1>
      <div className="card p-4 mt-4 space-y-3">
        <input className="input" value={name} onChange={(e) => setName(e.target.value)} />
        <select className="input max-w-xs" value={type} onChange={(e) => setType(e.target.value)}>
          <option value="dynamic">Dynamic</option>
          <option value="static">Static</option>
        </select>
        {filters.map((f, i) => (
          <div key={i} className="flex flex-wrap gap-2">
            <select className="input max-w-[180px]" value={f.field} onChange={(e) => setFilters(filters.map((x, j) => (j === i ? { ...x, field: e.target.value } : x)))}>
              {FIELDS.map(([k, l]) => (
                <option key={k} value={k}>
                  {l}
                </option>
              ))}
            </select>
            <select className="input max-w-[140px]" value={f.op} onChange={(e) => setFilters(filters.map((x, j) => (j === i ? { ...x, op: e.target.value } : x)))}>
              {OPS.map((o) => (
                <option key={o}>{o}</option>
              ))}
            </select>
            <input className="input max-w-xs" value={f.value} onChange={(e) => setFilters(filters.map((x, j) => (j === i ? { ...x, value: e.target.value } : x)))} />
          </div>
        ))}
        <button className="btn btn-ghost" onClick={() => setFilters([...filters, { field: "location", op: "contains", value: "" }])}>
          Add filter
        </button>
        {err && <p className="text-sm text-red-600">{err}</p>}
        <div className="flex gap-2">
          <button
            className="btn btn-ghost"
            onClick={async () => {
              const { data } = await api.post("/segments/preview", body);
              setPreview(data);
            }}
          >
            Preview
          </button>
          <button
            className="btn btn-primary"
            onClick={async () => {
              setErr("");
              try {
                if (editId) await api.patch(`/segments/${editId}`, body);
                else await api.post("/segments", body);
                setEditId(null);
                await load();
              } catch (e: any) {
                setErr(e.response?.data?.error?.message || "Save failed");
              }
            }}
          >
            Save segment
          </button>
        </div>
        {preview && <p className="text-sm">Matching leads: {preview.count}</p>}
      </div>
      {rows.map((s) => (
        <div key={s.id} className="card p-4 mt-3">
          <div className="font-medium">
            {s.name} · {s.type} · {s.active === false ? "inactive" : "active"} · Matching leads: {s.count}
          </div>
          <div className="text-xs text-gray-500 mt-1">Created {s.created_at} · Updated {s.updated_at || s.created_at}</div>
          <div className="text-sm text-gray-600 mt-1">{JSON.stringify(s.filters)}</div>
          <div className="text-sm text-gray-600">{(s.leads || []).map((l: any) => l.company).join(", ") || "Empty"}</div>
          <div className="flex gap-2 mt-2">
            <button
              className="btn btn-ghost"
              onClick={() => {
                setEditId(s.id);
                setName(s.name);
                setType(s.type);
                setFilters(Array.isArray(s.filters) ? s.filters : [{ field: "location", op: "contains", value: s.filters?.location_contains || "India" }]);
              }}
            >
              Edit
            </button>
            <button
              className="btn btn-ghost"
              onClick={async () => {
                await api.delete(`/segments/${s.id}`);
                load();
              }}
            >
              Delete
            </button>
            <button
              className="btn btn-ghost"
              onClick={async () => {
                const res = await api.get("/leads/export", { params: { format: "csv", segment_id: s.id }, responseType: "blob" });
                const url = URL.createObjectURL(res.data);
                const a = document.createElement("a");
                a.href = url;
                a.download = "segment.csv";
                a.click();
              }}
            >
              Export CSV
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
