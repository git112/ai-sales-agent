import { useState, useRef } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Upload, FileSpreadsheet, CheckCircle2, AlertTriangle, ArrowLeft, Check, FileCheck, X } from "lucide-react";
import { api } from "../api";

export default function ImportLeads() {
  const nav = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<any>(null);
  const [mapping, setMapping] = useState<any>({});
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [err, setErr] = useState("");
  const [dragActive, setDragActive] = useState(false);

  async function handleFile(file: File) {
    if (!file) return;
    setSelectedFile(file);
    setUploading(true);
    setErr("");
    try {
      const fd = new FormData();
      fd.append("file", file);
      const { data } = await api.post("/leads/import/preview", fd);
      setPreview(data);
      setMapping(data.mapping);
    } catch (e: any) {
      setErr(e.response?.data?.error?.message || "Failed to parse file. Please upload a valid CSV or Excel file.");
    } finally {
      setUploading(false);
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  }

  return (
    <div className="max-w-4xl space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link
          to="/app/leads"
          className="p-2 rounded-xl bg-white border border-slate-200 text-slate-500 hover:text-slate-800 transition shadow-xs"
        >
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Import Leads & Prospects</h1>
          <p className="text-sm text-slate-500">Upload CSV or Excel spreadsheets, validate column mapping, and import clean records.</p>
        </div>
      </div>

      {/* Modern Choose File Dropzone */}
      <div
        onDragEnter={(e) => { e.preventDefault(); setDragActive(true); }}
        onDragLeave={(e) => { e.preventDefault(); setDragActive(false); }}
        onDragOver={(e) => { e.preventDefault(); }}
        onDrop={handleDrop}
        className={`card p-8 bg-white border-2 border-dashed transition-all text-center ${
          dragActive
            ? "border-indigo-500 bg-indigo-50/40 ring-4 ring-indigo-500/10"
            : "border-slate-200 hover:border-indigo-300"
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.xlsx"
          className="hidden"
          onChange={(e) => {
            if (e.target.files?.[0]) handleFile(e.target.files[0]);
          }}
        />

        <div className="max-w-md mx-auto space-y-3">
          <div className="w-14 h-14 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center mx-auto shadow-xs">
            <FileSpreadsheet className="w-7 h-7" />
          </div>

          <div>
            <h3 className="font-bold text-slate-800 text-base">Select your prospect dataset</h3>
            <p className="text-xs text-slate-500 mt-1">Supports CSV and XLSX spreadsheets up to 25MB.</p>
          </div>

          <div className="flex items-center justify-center gap-3 pt-2">
            <button
              type="button"
              className="btn btn-primary text-xs py-2 px-4 flex items-center gap-2 shadow-xs"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
            >
              <Upload className="w-4 h-4" />
              <span>{uploading ? "Analyzing File…" : "Choose File"}</span>
            </button>
            <span className="text-xs text-slate-400 font-medium">or drag and drop here</span>
          </div>

          {selectedFile && (
            <div className="mt-4 p-2.5 bg-slate-50 border border-slate-200 rounded-xl inline-flex items-center gap-2.5 text-xs text-slate-700">
              <FileCheck className="w-4 h-4 text-emerald-600" />
              <span className="font-semibold text-slate-900">{selectedFile.name}</span>
              <span className="text-slate-400">({(selectedFile.size / 1024).toFixed(1)} KB)</span>
              <button
                type="button"
                onClick={() => {
                  setSelectedFile(null);
                  setPreview(null);
                  if (fileInputRef.current) fileInputRef.current.value = "";
                }}
                className="text-slate-400 hover:text-slate-600 ml-1"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>
      </div>

      {err && (
        <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs font-semibold text-rose-800 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{err}</span>
        </div>
      )}

      {/* Preview & Column Mapping */}
      {preview && (
        <div className="card p-6 bg-white shadow-xs space-y-6">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h2 className="font-bold text-slate-900 text-base">File Verification & Column Mapping</h2>
              <p className="text-xs text-slate-500">Confirm field alignment before committing records to the workspace pipeline.</p>
            </div>
          </div>

          {/* KPI Metrics */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="card p-3 bg-slate-50 border-slate-200 text-center">
              <div className="text-[11px] font-semibold text-slate-500 uppercase">Total Rows</div>
              <div className="text-xl font-bold text-slate-900 mt-1">{preview.total_rows ?? preview.count}</div>
            </div>
            <div className="card p-3 bg-emerald-50 border-emerald-200 text-center">
              <div className="text-[11px] font-semibold text-emerald-700 uppercase">Valid Rows</div>
              <div className="text-xl font-bold text-emerald-800 mt-1">{preview.valid_rows}</div>
            </div>
            <div className="card p-3 bg-rose-50 border-rose-200 text-center">
              <div className="text-[11px] font-semibold text-rose-700 uppercase">Invalid Rows</div>
              <div className="text-xl font-bold text-rose-800 mt-1">{preview.invalid_rows}</div>
            </div>
            <div className="card p-3 bg-amber-50 border-amber-200 text-center">
              <div className="text-[11px] font-semibold text-amber-700 uppercase">Duplicate Rows</div>
              <div className="text-xl font-bold text-amber-800 mt-1">{preview.duplicate_rows}</div>
            </div>
          </div>

          {/* Column Mapping Grid */}
          <div className="space-y-3">
            <h3 className="font-bold text-slate-900 text-sm">Target Fields Mapping</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {Object.keys(mapping).map((f) => (
                <div key={f} className="flex items-center justify-between gap-3 p-2.5 bg-slate-50 rounded-xl border border-slate-200/80">
                  <span className="text-xs font-semibold text-slate-700 capitalize w-28 truncate">{f}</span>
                  <select
                    className="input h-9 text-xs font-medium bg-white flex-1"
                    value={mapping[f] || ""}
                    onChange={(e) => setMapping({ ...mapping, [f]: e.target.value })}
                  >
                    <option value="">— Unmapped —</option>
                    {preview.headers.map((h: string) => (
                      <option key={h} value={h}>{h}</option>
                    ))}
                  </select>
                </div>
              ))}
            </div>
          </div>

          {/* Validation Warnings / Errors Table */}
          {(preview.errors || []).length > 0 && (
            <div className="space-y-2 pt-2">
              <h3 className="font-bold text-slate-900 text-sm flex items-center gap-1.5 text-amber-800">
                <AlertTriangle className="w-4 h-4 text-amber-600" />
                <span>Detected Validation Issues ({preview.errors.length})</span>
              </h3>
              <div className="overflow-x-auto border border-slate-200 rounded-xl">
                <table className="w-full text-xs">
                  <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200 text-left">
                    <tr>
                      <th className="p-3">Row</th>
                      <th className="p-3">Field</th>
                      <th className="p-3">Problem</th>
                      <th className="p-3">Suggested Correction</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {preview.errors.map((e: any, i: number) => (
                      <tr key={i} className="hover:bg-slate-50">
                        <td className="p-3 font-semibold text-slate-800">#{e.row}</td>
                        <td className="p-3 text-slate-600 font-medium">{e.field}</td>
                        <td className="p-3 text-rose-600">{e.problem}</td>
                        <td className="p-3 text-slate-700">{e.suggested || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-slate-100">
            <div className="text-xs text-slate-500">
              💡 <strong>Own Leads Mode:</strong> Upload prospect lists directly for AI Calling without needing AI lead discovery.
            </div>
            <div className="flex items-center gap-2">
              <button className="btn btn-ghost text-xs" onClick={() => nav("/app/leads")}>
                Cancel
              </button>
              <button
                className="btn btn-ghost text-xs border border-indigo-200 text-indigo-700 hover:bg-indigo-50"
                disabled={busy}
                onClick={async () => {
                  setBusy(true);
                  setErr("");
                  try {
                    await api.post("/leads/import", { mapping, rows: (preview.preview || []).map((p: any) => p.row) });
                    nav("/app/campaigns/new");
                  } catch (e: any) {
                    setErr(e.response?.data?.error?.message || "Import failed");
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                <span>Import & Launch AI Calling Campaign</span>
              </button>
              <button
                className="btn btn-primary text-xs px-5 flex items-center gap-1.5"
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
                <Check className="w-4 h-4" />
                <span>{busy ? "Importing…" : "Import Valid Leads"}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
