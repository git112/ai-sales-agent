import { useEffect, useState } from "react";
import { Layers, Plus, Filter, Download, Trash2, Edit3, CheckCircle2 } from "lucide-react";
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
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-indigo-50 text-indigo-600 border border-indigo-100">
            <Layers className="w-5 h-5" />
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Lead Segments & Cohorts</h1>
        </div>
        <p className="text-sm text-slate-500 mt-1">
          Dynamic criteria-based filtering and static target groups for targeted outreach campaigns.
        </p>
      </div>
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
        {preview && <p className="text-xs font-semibold text-indigo-700 bg-indigo-50 border border-indigo-200 px-3 py-1.5 rounded-lg inline-block">Matching leads: {preview.count}</p>}
      </div>

      <div className="space-y-3">
        <h2 className="font-bold text-slate-900 text-sm uppercase tracking-wider">Configured Segments ({rows.length})</h2>
        {rows.map((s) => (
          <div key={s.id} className="card p-5 bg-white shadow-xs space-y-2.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="font-bold text-slate-900 text-base">{s.name}</span>
                <span className="badge bg-indigo-50 text-indigo-700 border border-indigo-200">{s.type}</span>
                <span className={`badge ${s.active === false ? "bg-slate-100 text-slate-600" : "bg-emerald-50 text-emerald-700 border border-emerald-200"}`}>
                  {s.active === false ? "inactive" : "active"}
                </span>
              </div>
              <span className="text-xs font-bold text-indigo-600 bg-indigo-50 px-2.5 py-1 rounded-full border border-indigo-100">
                {s.count ?? 0} leads
              </span>
            </div>

            <div className="text-xs text-slate-500 font-medium">
              Created {s.created_at} · Updated {s.updated_at || s.created_at}
            </div>

            <div className="p-2.5 bg-slate-50 border border-slate-200/80 rounded-lg text-xs font-mono text-slate-700 overflow-x-auto">
              {JSON.stringify(s.filters)}
            </div>

            <div className="flex items-center justify-between pt-1">
              <div className="text-xs text-slate-500 truncate max-w-md">
                {(s.leads || []).map((l: any) => l.company).join(", ") || "No leads matched yet"}
              </div>
              <div className="flex gap-2">
                <button
                  className="btn btn-ghost text-xs py-1.5 px-3 flex items-center gap-1"
                  onClick={() => {
                    setEditId(s.id);
                    setName(s.name);
                    setType(s.type);
                    setFilters(Array.isArray(s.filters) ? s.filters : [{ field: "location", op: "contains", value: s.filters?.location_contains || "India" }]);
                  }}
                >
                  <Edit3 className="w-3.5 h-3.5" />
                  Edit
                </button>
                <button
                  className="btn btn-ghost text-xs py-1.5 px-3 flex items-center gap-1"
                  onClick={async () => {
                    const res = await api.get("/leads/export", { params: { format: "csv", segment_id: s.id }, responseType: "blob" });
                    const url = URL.createObjectURL(res.data);
                    const a = document.createElement("a");
                    a.href = url;
                    a.download = "segment.csv";
                    a.click();
                  }}
                >
                  <Download className="w-3.5 h-3.5" />
                  CSV
                </button>
                <button
                  className="btn btn-danger text-xs py-1.5 px-2.5 flex items-center gap-1"
                  onClick={async () => {
                    if (confirm("Delete this segment?")) {
                      await api.delete(`/segments/${s.id}`);
                      load();
                    }
                  }}
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
