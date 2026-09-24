import { useEffect, useState, useRef } from "react";
import { BookOpen, Upload, FileText, Trash2, Search, Sparkles, CheckCircle2, X } from "lucide-react";
import { api } from "../api";

export default function Knowledge() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [rows, setRows] = useState<any[]>([]);
  const [q, setQ] = useState("SharePoint migration");
  const [chunks, setChunks] = useState<string[]>([]);
  const [uploading, setUploading] = useState(false);
  const [searching, setSearching] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  async function load() {
    const { data } = await api.get("/knowledge");
    setRows(data);
  }

  useEffect(() => {
    load();
  }, []);

  async function handleFile(file: File) {
    if (!file) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      await api.post("/knowledge/upload", fd);
      load();
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-indigo-50 text-indigo-600 border border-indigo-100">
            <BookOpen className="w-5 h-5" />
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Enterprise Knowledge Base</h1>
        </div>
        <p className="text-sm text-slate-500 mt-1">
          Upload product documentation, solution sheets, and pricing collateral to ground voice agent conversations.
        </p>
      </div>

      {/* Modern Choose File Dropzone */}
      <div
        onDragEnter={(e) => { e.preventDefault(); setDragActive(true); }}
        onDragLeave={(e) => { e.preventDefault(); setDragActive(false); }}
        onDragOver={(e) => { e.preventDefault(); }}
        onDrop={(e) => {
          e.preventDefault();
          setDragActive(false);
          if (e.dataTransfer.files?.[0]) handleFile(e.dataTransfer.files[0]);
        }}
        className={`card p-8 bg-white border-2 border-dashed transition-all text-center ${
          dragActive
            ? "border-indigo-500 bg-indigo-50/40 ring-4 ring-indigo-500/10"
            : "border-slate-200 hover:border-indigo-300"
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.txt"
          className="hidden"
          onChange={(e) => {
            if (e.target.files?.[0]) handleFile(e.target.files[0]);
          }}
        />

        <div className="max-w-md mx-auto space-y-3">
          <div className="w-14 h-14 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center mx-auto shadow-xs">
            <FileText className="w-7 h-7" />
          </div>

          <div>
            <h3 className="font-bold text-slate-800 text-base">Add Document to Knowledge Store</h3>
            <p className="text-xs text-slate-500 mt-1">Supports PDF, DOCX, and TXT documentation files.</p>
          </div>

          <div className="flex items-center justify-center gap-3 pt-2">
            <button
              type="button"
              className="btn btn-primary text-xs py-2 px-4 flex items-center gap-2 shadow-xs"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
            >
              <Upload className="w-4 h-4" />
              <span>{uploading ? "Ingesting & Chunking…" : "Choose Document"}</span>
            </button>
            <span className="text-xs text-slate-400 font-medium">or drag and drop here</span>
          </div>
        </div>
      </div>

      {/* Uploaded Documents */}
      <div className="space-y-3">
        <h2 className="font-bold text-slate-900 text-base">Indexed Documents ({rows.length})</h2>
        {rows.length === 0 ? (
          <p className="text-sm text-slate-400 py-4 text-center">No documents uploaded yet.</p>
        ) : (
          rows.map((d) => (
            <div
              key={d.id}
              className="card p-4 bg-white shadow-xs hover:border-slate-300 transition-all flex items-center justify-between gap-4"
            >
              <div className="flex items-center gap-3 min-w-0">
                <div className="p-2.5 rounded-xl bg-slate-100 text-slate-700 shrink-0">
                  <FileText className="w-5 h-5 text-indigo-600" />
                </div>
                <div className="min-w-0">
                  <div className="font-bold text-slate-900 text-sm truncate">{d.filename}</div>
                  <div className="flex items-center gap-3 text-xs text-slate-400 mt-0.5">
                    <span className="badge bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px]">
                      {d.status || "Indexed"}
                    </span>
                    <span>{d.chunk_count} semantic chunks</span>
                    <span>{d.type || "Document"}</span>
                  </div>
                </div>
              </div>

              <button
                className="btn btn-ghost text-xs py-1.5 px-2.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition shrink-0"
                title="Delete document"
                onClick={async () => {
                  await api.delete(`/knowledge/${d.id}`);
                  load();
                }}
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))
        )}
      </div>

      {/* Semantic Search Grounding Tester */}
      <div className="card p-5 bg-white shadow-xs space-y-4">
        <div>
          <h2 className="font-bold text-slate-900 text-base flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-indigo-600" />
            Semantic Retrieval Test
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Test semantic matching against indexed knowledge chunks for grounding agent queries.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              className="input search-input h-11 pr-10"
              placeholder="Search knowledge store..."
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onKeyDown={async (e) => {
                if (e.key === "Enter") {
                  setSearching(true);
                  try {
                    const res = await api.get("/knowledge/search", { params: { q } });
                    setChunks(res.data.chunks || []);
                  } finally {
                    setSearching(false);
                  }
                }
              }}
            />
            {q && (
              <button
                type="button"
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 p-1 rounded-md transition-colors"
                onClick={() => setQ("")}
                title="Clear search"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
          <button
            className="btn btn-primary h-11 px-5 text-xs font-semibold"
            disabled={searching}
            onClick={async () => {
              setSearching(true);
              try {
                const res = await api.get("/knowledge/search", { params: { q } });
                setChunks(res.data.chunks || []);
              } finally {
                setSearching(false);
              }
            }}
          >
            {searching ? "Searching…" : "Retrieve Chunks"}
          </button>
        </div>

        {chunks.length > 0 && (
          <div className="space-y-2 pt-2">
            <div className="text-xs font-semibold text-slate-500 uppercase">Retrieved Context Passages</div>
            {chunks.map((c, i) => (
              <div key={i} className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-700 leading-relaxed">
                {c}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
