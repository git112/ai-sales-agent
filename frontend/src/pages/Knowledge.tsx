import { useEffect, useState } from "react";
import { api } from "../api";

export default function Knowledge() {
  const [rows, setRows] = useState<any[]>([]);
  const [q, setQ] = useState("SharePoint migration");
  const [chunks, setChunks] = useState<string[]>([]);
  useEffect(() => {
    api.get("/knowledge").then((r) => setRows(r.data));
  }, []);
  return (
    <div>
      <h1 className="text-2xl font-semibold">Knowledge base</h1>
      <input
        className="mt-4"
        type="file"
        accept=".pdf,.docx,.txt"
        onChange={async (e) => {
          const file = e.target.files?.[0];
          if (!file) return;
          const fd = new FormData();
          fd.append("file", file);
          await api.post("/knowledge/upload", fd);
          setRows((await api.get("/knowledge")).data);
        }}
      />
      {rows.map((d) => (
        <div key={d.id} className="card p-4 mt-3 flex justify-between">
          <div>
            <div className="font-medium">{d.filename}</div>
            <div className="text-xs text-gray-500">
              {d.status} · {d.chunk_count} chunks · {d.type}
            </div>
          </div>
          <button className="btn btn-ghost" onClick={() => api.delete(`/knowledge/${d.id}`).then(() => api.get("/knowledge").then((r) => setRows(r.data)))}>
            Delete
          </button>
        </div>
      ))}
      <div className="flex gap-2 mt-6">
        <input className="input" value={q} onChange={(e) => setQ(e.target.value)} />
        <button className="btn btn-primary" onClick={async () => setChunks((await api.get("/knowledge/search", { params: { q } })).data.chunks)}>
          Search
        </button>
      </div>
      {chunks.map((c, i) => (
        <p key={i} className="text-sm card p-3 mt-2">
          {c}
        </p>
      ))}
    </div>
  );
}
