import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Megaphone, Play, Pause, PhoneCall, FastForward, Clock, ArrowUpRight, Flame, CheckCircle2 } from "lucide-react";
import { api } from "../api";

const OUTCOMES = ["Connected", "No Answer", "Voicemail", "Callback Requested", "Not Interested", "Interested", "Escalated"];

export default function CampaignDetail() {
  const { id } = useParams();
  const [camp, setCamp] = useState<any>(null);
  const [result, setResult] = useState<any>(null);
  const [hint, setHint] = useState("Interested");
  const [busy, setBusy] = useState("");
  const [err, setErr] = useState("");
  const [callLang, setCallLang] = useState("auto");

  useEffect(() => {
    api.get(`/campaigns/${id}`).then((r) => setCamp(r.data));
  }, [id]);

  if (!camp) {
    return (
      <div className="flex items-center justify-center min-h-[300px] text-slate-500 text-sm">
        Loading campaign parameters…
      </div>
    );
  }

  const leadId = camp.lead_ids?.[0] || "lead_abc";
  const timeline = camp.timeline || [];

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-indigo-50 text-indigo-600 border border-indigo-100">
              <Megaphone className="w-5 h-5" />
            </div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">{camp.name}</h1>
            <span className="badge bg-emerald-50 text-emerald-700 border border-emerald-200">
              {camp.status || "Active"}
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            {camp.campaign_type} · Schedule: {camp.schedule} · TZ: {camp.timezone} · Quiet: {camp.quiet_hours?.start}-{camp.quiet_hours?.end}
          </p>
        </div>

        {/* Campaign Control Buttons */}
        <div className="flex items-center gap-2">
          <button
            className="btn btn-primary text-xs py-2 px-3 flex items-center gap-1.5"
            onClick={() => api.post(`/campaigns/${id}/launch`).then((r) => setCamp(r.data))}
          >
            <Play className="w-3.5 h-3.5" />
            <span>Launch</span>
          </button>
          <button
            className="btn btn-ghost text-xs py-2 px-3 flex items-center gap-1.5"
            onClick={() => api.post(`/campaigns/${id}/pause`).then((r) => setCamp(r.data))}
          >
            <Pause className="w-3.5 h-3.5" />
            <span>Pause</span>
          </button>
          <button
            className="btn btn-ghost text-xs py-2 px-3"
            onClick={() => api.post(`/campaigns/${id}/resume`).then((r) => setCamp(r.data))}
          >
            Resume
          </button>
        </div>
      </div>

      {/* Voice Console Card */}
      <div className="card p-6 bg-white shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-indigo-50 text-indigo-600">
              <PhoneCall className="w-4 h-4" />
            </div>
            <h2 className="font-bold text-slate-900 text-base">Voice Qualification Console</h2>
          </div>
          <span className="badge bg-indigo-50 text-indigo-700 border border-indigo-200/60">
            Interactive Runner
          </span>
        </div>
        <p className="text-sm text-slate-500">
          Execute conversational outreach sequences, evaluate interest indicators, and log qualification steps.
        </p>

        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 pt-2">
          <div className="w-full sm:w-56">
            <label className="block text-xs font-semibold text-slate-700 mb-1">Target Outcome Trigger</label>
            <select className="input h-10 text-xs font-medium" value={hint} onChange={(e) => setHint(e.target.value)}>
              {OUTCOMES.map((h) => (
                <option key={h} value={h}>{h}</option>
              ))}
            </select>
          </div>

          <div className="w-full sm:w-56">
            <label className="block text-xs font-semibold text-slate-700 mb-1">Call Language</label>
            <select className="input h-10 text-xs font-medium" value={callLang} onChange={(e) => setCallLang(e.target.value)}>
              <option value="auto">Auto-detect from Lead</option>
              <option value="en">English (US/UK/Global)</option>
              <option value="hi">Hindi (हिन्दी)</option>
              <option value="gu">Gujarati (ગુજરાતી)</option>
              <option value="es">Spanish (Español)</option>
              <option value="fr">French (Français)</option>
              <option value="de">German (Deutsch)</option>
            </select>
          </div>

          <div className="flex items-end gap-2 pt-5">
            <button
              className="btn btn-primary h-10 px-4 text-xs font-semibold flex items-center gap-1.5"
              disabled={busy === "sim"}
              onClick={async () => {
                setBusy("sim");
                setErr("");
                try {
                  const { data } = await api.post(`/campaigns/${id}/calls/simulate`, {
                    lead_id: leadId,
                    outcome_hint: hint,
                    language: callLang,
                  });
                  setResult(data);
                } catch (e: any) {
                  setErr(e.response?.data?.error?.message || "Simulation failed");
                } finally {
                  setBusy("");
                }
              }}
            >
              <PhoneCall className="w-3.5 h-3.5" />
              <span>{busy === "sim" ? "Executing…" : "Initiate Call"}</span>
            </button>

            <button
              className="btn btn-ghost h-10 px-4 text-xs font-semibold flex items-center gap-1.5"
              disabled={busy === "step"}
              onClick={async () => {
                setBusy("step");
                setErr("");
                try {
                  const { data } = await api.post(`/campaigns/${id}/next-step`, {}, { params: { lead_id: leadId, force: true } });
                  setResult(data.result || data);
                  setCamp(data.campaign || camp);
                } catch (e: any) {
                  setErr(e.response?.data?.error?.message || "Step failed");
                } finally {
                  setBusy("");
                }
              }}
            >
              <FastForward className="w-3.5 h-3.5 text-slate-500" />
              <span>{busy === "step" ? "Advancing…" : "Advance Next Step"}</span>
            </button>
          </div>
        </div>

        {err && <p className="text-sm text-rose-600 mt-2 font-medium">{err}</p>}
      </div>

      {/* Result Card */}
      {result && (
        <div className="card p-5 bg-white border-l-4 border-l-indigo-600 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <span className="badge bg-indigo-50 text-indigo-700 border border-indigo-200">
              {result.label || "Call Logged"}
            </span>
            {result.qualification?.high_intent && (
              <span className="badge bg-amber-50 text-amber-700 border border-amber-200">
                <Flame className="w-3 h-3 text-amber-600" />
                HIGH INTENT PROSPECT
              </span>
            )}
          </div>

          <p className="text-sm text-slate-700 leading-relaxed font-medium">
            {result.transcript?.summary || result.call?.outcome}
          </p>

          {/* Real-time Dialogue Transcript */}
          {result.transcript?.turns && result.transcript.turns.length > 0 && (
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 space-y-2 max-h-60 overflow-y-auto">
              <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Live Call Transcript</div>
              {result.transcript.turns.map((turn: any, idx: number) => (
                <div
                  key={idx}
                  className={`text-xs p-2 rounded-lg max-w-[85%] ${
                    turn.speaker === "agent"
                      ? "bg-indigo-50/80 text-indigo-950 border border-indigo-100"
                      : "bg-white text-slate-800 border border-slate-200 ml-auto shadow-xs"
                  }`}
                >
                  <div className="text-[10px] font-semibold text-slate-400 uppercase mb-0.5">
                    {turn.speaker === "agent" ? "🤖 AI Assistant" : "👤 Prospect"}
                  </div>
                  <div className="leading-snug">{turn.text}</div>
                </div>
              ))}
            </div>
          )}

          {/* Negative Call or Human Handoff Banner */}
          {result.call?.escalated && (
            <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-800 flex items-center justify-between">
              <div>
                <strong>👤 Human Handoff Triggered:</strong> {result.call?.handoff_reason || "Prospect requested specialist"}
              </div>
              <span className="badge bg-amber-200 text-amber-900 border-none font-bold">Transfer Queue</span>
            </div>
          )}
          {result.call?.outcome === "Not Interested" && (
            <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-800 flex items-center justify-between">
              <div>
                <strong>🚫 Negative Outreach Handled:</strong> Outreach ceased & number placed on Do-Not-Contact list.
              </div>
              <span className="badge bg-rose-200 text-rose-900 border-none font-bold">Opted Out</span>
            </div>
          )}

          <div className="text-xs text-slate-500 flex items-center gap-4 pt-1">
            {result.next_best_action && (
              <div>
                <span className="font-semibold text-slate-700">Next Action:</span> {result.next_best_action?.action}
              </div>
            )}
            {result.task && (
              <div>
                <span className="font-semibold text-slate-700">Task:</span> {result.task.title} (Due: {result.task.due})
              </div>
            )}
          </div>

          {result.call && (
            <div className="pt-2">
              <Link
                className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-600 hover:text-indigo-800"
                to={`/app/calls/${result.call.id}`}
              >
                <span>Review Full Transcript & Analysis</span>
                <ArrowUpRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          )}
        </div>
      )}

      {/* Campaign Timeline */}
      <div className="card p-5 bg-white shadow-xs">
        <h2 className="font-bold text-slate-900 text-base mb-3 flex items-center gap-2">
          <Clock className="w-4 h-4 text-indigo-600" />
          Campaign Execution Timeline
        </h2>
        {timeline.length === 0 ? (
          <p className="text-sm text-slate-400 py-4 text-center">No campaign attempts logged yet.</p>
        ) : (
          <div className="divide-y divide-slate-100">
            {timeline.map((t: any, i: number) => (
              <div key={i} className="py-2.5 flex items-center justify-between text-xs text-slate-700">
                <div className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-indigo-600"></span>
                  <span className="font-semibold text-slate-900">Attempt {t.attempt}:</span>
                  <span>{t.outcome}</span>
                  {t.retry_scheduled && <span className="text-slate-400">· Retry scheduled</span>}
                </div>
                {t.outcome === "Interested" && (
                  <span className="badge bg-amber-50 text-amber-700 border border-amber-200">
                    High Intent
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
