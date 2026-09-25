import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import {
  Bot,
  User,
  PhoneCall,
  CalendarClock,
  ExternalLink,
  Send,
  AlertTriangle,
  ShieldOff,
  PhoneOff,
  CheckCircle2,
  XCircle,
  Voicemail,
  Phone,
} from "lucide-react";
import { api } from "../api";

type Turn = { speaker: string; text: string; ts?: string };

function formatTime(iso?: string) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function formatSeconds(sec: number | string) {
  const n = Number(sec) || 0;
  if (n < 60) return `${n}s`;
  const m = Math.floor(n / 60);
  const s = n % 60;
  return `${m}m ${s.toString().padStart(2, "0")}s`;
}

function outcomeMeta(outcome: string) {
  const map: Record<string, { color: string; icon: any; label: string }> = {
    Interested:        { color: "bg-emerald-50 text-emerald-700 border-emerald-200", icon: CheckCircle2, label: "Interested" },
    Connected:         { color: "bg-emerald-50 text-emerald-700 border-emerald-200", icon: CheckCircle2, label: "Connected" },
    "Callback Scheduled": { color: "bg-violet-50 text-violet-700 border-violet-200",   icon: CalendarClock, label: "Callback Scheduled" },
    Escalated:         { color: "bg-indigo-50 text-indigo-700 border-indigo-200",       icon: PhoneCall,     label: "Escalated" },
    "Callback Requested": { color: "bg-amber-50 text-amber-700 border-amber-200",       icon: Phone,         label: "Callback Requested" },
    Voicemail:         { color: "bg-slate-100 text-slate-700 border-slate-200",         icon: Voicemail,     label: "Voicemail" },
    "No Answer":       { color: "bg-slate-100 text-slate-700 border-slate-200",         icon: PhoneOff,      label: "No Answer" },
    "Not Interested":  { color: "bg-rose-50 text-rose-700 border-rose-200",             icon: XCircle,       label: "Not Interested" },
  };
  return map[outcome] || { color: "bg-slate-100 text-slate-700 border-slate-200", icon: PhoneCall, label: outcome || "Unknown" };
}

function normalizeSpeaker(raw: string): "agent" | "prospect" {
  const s = (raw || "").toLowerCase();
  if (s.includes("agent") || s.includes("assistant") || s.includes("ai") || s.includes("bot")) return "agent";
  if (s.includes("user") || s.includes("prospect") || s.includes("customer") || s.includes("lead")) return "prospect";
  return s === "agent" ? "agent" : "prospect";
}

function stripSpeakerPrefix(text: string): string {
  return text.replace(/^\s*(assistant|agent|user|prospect|ai|bot)\s*:\s*/i, "").trim();
}

export default function CallDetail() {
  const { id } = useParams();
  const [data, setData] = useState<any>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "agent" | "prospect">("all");

  const reload = () => api.get(`/calls/${id}`).then((r) => setData(r.data));

  useEffect(() => {
    reload();
  }, [id]);

  const action = async (path: string, key: string) => {
    setBusy(key);
    try {
      await api.post(path);
      await reload();
    } finally {
      setBusy(null);
    }
  };

  const turns: Turn[] = useMemo(() => {
    const raw: Turn[] = data?.transcript?.turns || [];
    return raw.map((t) => ({
      speaker: normalizeSpeaker(t.speaker || ""),
      text: stripSpeakerPrefix(t.text || ""),
      ts: t.ts,
    }));
  }, [data]);

  if (!data) return <p className="text-slate-500">Loading…</p>;
  const { call, transcript, qualification } = data;
  const meta = outcomeMeta(call.outcome);
  const MetaIcon = meta.icon;

  const isAgent = (t: Turn) => t.speaker === "agent";
  const requestedSlot = call.requested_slot || transcript?.requested_slot;

  return (
    <div className="space-y-5 max-w-4xl">
      {/* ── Header ─────────────────────────────────────────── */}
      <div className="card p-5 bg-white">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <div className="p-2.5 rounded-xl bg-indigo-50 text-indigo-600 border border-indigo-100">
              <PhoneCall className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h1 className="text-xl font-bold text-slate-900 tracking-tight">
                  {call.label || "Call"}
                </h1>
                <span className={`badge ${meta.color}`}>
                  <MetaIcon className="w-3 h-3 mr-1" />
                  {meta.label}
                </span>
                {qualification?.high_intent && (
                  <span className="badge bg-amber-50 text-amber-800 border border-amber-200">
                    HIGH INTENT
                  </span>
                )}
                {call.mode === "live" && (
                  <span className="badge bg-violet-50 text-violet-700 border border-violet-200">
                    Live Bolna
                  </span>
                )}
              </div>
              <div className="flex items-center gap-4 mt-1.5 text-xs text-slate-500">
                <span>Started {formatTime(call.started_at)}</span>
                <span>·</span>
                <span>{formatSeconds(call.duration_sec)}</span>
                {call.recording_url && (
                  <>
                    <span>·</span>
                    <a href={call.recording_url} target="_blank" rel="noreferrer" className="text-indigo-600 hover:text-indigo-800 font-medium inline-flex items-center gap-1">
                      Recording <ExternalLink className="w-3 h-3" />
                    </a>
                  </>
                )}
              </div>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              className="btn btn-ghost"
              disabled={busy === "handoff"}
              onClick={() => action(`/calls/${id}/handoff`, "handoff")}
            >
              <Send className="w-3.5 h-3.5" />
              {busy === "handoff" ? "Dispatching…" : "Human handoff"}
            </button>
            <button
              className="btn btn-ghost text-rose-700 hover:bg-rose-50"
              disabled={busy === "opt"}
              onClick={() => action(`/calls/${id}/opt-out`, "opt")}
            >
              <ShieldOff className="w-3.5 h-3.5" />
              {busy === "opt" ? "Recording…" : "Record opt-out"}
            </button>
          </div>
        </div>
      </div>

      {/* ── Escalation banner ──────────────────────────────── */}
      {call.escalated && (
        <div className="card p-3.5 bg-indigo-50/60 border-indigo-200">
          <div className="flex items-start gap-2.5">
            <PhoneCall className="w-4 h-4 text-indigo-600 mt-0.5" />
            <div className="text-sm">
              <div className="font-semibold text-indigo-900">Escalated to human</div>
              <div className="text-indigo-700/80">
                {call.handoff_reason || "Prospect requested a human specialist"}
                {call.escalated_at ? ` · ${formatTime(call.escalated_at)}` : ""}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Calendly / callback chip ───────────────────────── */}
      {(call.calendly_link || call.calendly_booking_id || requestedSlot) && (
        <div className="card p-4 bg-violet-50/40 border-violet-200">
          <div className="flex items-start justify-between gap-3 flex-wrap">
            <div className="flex items-start gap-2.5">
              <CalendarClock className="w-4 h-4 text-violet-600 mt-0.5" />
              <div className="text-sm">
                <div className="font-semibold text-violet-900">
                  {requestedSlot ? "Callback Scheduled" : call.calendly_status === "booked" ? "Calendly Booking Confirmed" : "Calendly Link Dispatched"}
                </div>
                {requestedSlot && (
                  <div className="text-violet-800 mt-0.5">
                    <span className="font-medium">{requestedSlot.label}</span>
                    {requestedSlot.raw && <span className="text-violet-700/70"> · “{requestedSlot.raw}”</span>}
                  </div>
                )}
                {call.calendly_slot && !requestedSlot && (
                  <div className="text-violet-800 mt-0.5">{call.calendly_slot}</div>
                )}
                {call.calendly_booking_id && (
                  <div className="text-xs text-violet-700/70 mt-1 font-mono">{call.calendly_booking_id}</div>
                )}
              </div>
            </div>
            {call.calendly_link && (
              <a
                href={call.calendly_link}
                target="_blank"
                rel="noreferrer"
                className="btn btn-primary text-xs"
              >
                <ExternalLink className="w-3 h-3" />
                Open link
              </a>
            )}
          </div>
        </div>
      )}

      {/* ── Voicemail ──────────────────────────────────────── */}
      {call.voicemail_message && (
        <div className="card p-4 bg-white">
          <div className="flex items-start gap-2.5">
            <Voicemail className="w-4 h-4 text-slate-500 mt-0.5" />
            <div className="text-sm">
              <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Approved Voicemail Message
              </div>
              <p className="text-slate-700 mt-1">{call.voicemail_message}</p>
            </div>
          </div>
        </div>
      )}

      {/* ── Summary / qualification ────────────────────────── */}
      {(transcript?.summary || transcript?.requirements || qualification) && (
        <div className="card p-4 bg-white">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold text-slate-900">Qualification Summary</h2>
            {qualification?.banner && (
              <span className="badge bg-amber-50 text-amber-800 border border-amber-200">
                {qualification.banner}
              </span>
            )}
          </div>
          {transcript?.summary && (
            <p className="text-sm text-slate-700 leading-relaxed">{transcript.summary}</p>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 mt-3 text-sm">
            <Field label="Interest Level" value={qualification?.interest_level || transcript?.interest_level} />
            <Field label="Requirements" value={transcript?.requirements || qualification?.requirements} />
            <Field label="Timeline" value={qualification?.timeline} />
            <Field label="Budget" value={qualification?.budget} />
            <Field label="Technology" value={qualification?.technology} />
            <Field label="Decision Stage" value={qualification?.decision_stage} />
          </div>
          {qualification?.evidence?.length > 0 && (
            <div className="mt-3 pt-3 border-t border-slate-100">
              <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Evidence</div>
              <ul className="space-y-1.5">
                {qualification.evidence.map((e: any, i: number) => (
                  <li key={i} className="text-xs text-slate-600 bg-slate-50 rounded-md p-2 border border-slate-100">
                    “{e.quote}” <span className="text-slate-400">— {e.source}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* ── Retry banner ───────────────────────────────────── */}
      {call.retry_eligible && (
        <div className="text-xs font-semibold text-amber-700 bg-amber-50 px-3 py-2 rounded-lg border border-amber-200 inline-flex items-center gap-2">
          <AlertTriangle className="w-3.5 h-3.5" />
          Sequence Active: Scheduled for retry attempt
        </div>
      )}

      {/* ── Transcript ─────────────────────────────────────── */}
      <div className="card p-4 bg-white">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-slate-900">
            Transcript
            <span className="ml-2 text-slate-400 font-normal text-xs">
              {turns.length} turn{turns.length === 1 ? "" : "s"}
            </span>
          </h2>
          <div className="inline-flex rounded-lg border border-slate-200 overflow-hidden text-xs">
            {(["all", "agent", "prospect"] as const).map((k) => (
              <button
                key={k}
                onClick={() => setFilter(k)}
                className={`px-3 py-1.5 font-medium capitalize transition-colors ${
                  filter === k
                    ? "bg-indigo-50 text-indigo-700"
                    : "bg-white text-slate-600 hover:bg-slate-50"
                }`}
              >
                {k}
              </button>
            ))}
          </div>
        </div>

        {turns.length === 0 ? (
          <p className="text-sm text-slate-400 py-6 text-center">No transcript captured.</p>
        ) : (
          <div className="space-y-2">
            {turns
              .filter((t) => filter === "all" || t.speaker === filter)
              .map((t, i) => {
                const Agent = t.speaker === "agent";
                return (
                  <div
                    key={i}
                    className={`flex gap-3 ${Agent ? "" : "flex-row-reverse"}`}
                  >
                    <div
                      className={`shrink-0 w-8 h-8 rounded-full flex items-center justify-center border ${
                        Agent
                          ? "bg-indigo-50 text-indigo-700 border-indigo-200"
                          : "bg-emerald-50 text-emerald-700 border-emerald-200"
                      }`}
                    >
                      {Agent ? <Bot className="w-4 h-4" /> : <User className="w-4 h-4" />}
                    </div>
                    <div className={`flex-1 max-w-[80%] ${Agent ? "" : "text-right"}`}>
                      <div className={`flex items-center gap-2 mb-1 ${Agent ? "" : "justify-end"}`}>
                        <span className="text-xs font-semibold text-slate-700">
                          {Agent ? "AI Agent" : "Prospect"}
                        </span>
                        {t.ts && (
                          <span className="text-xs text-slate-400">{formatTime(t.ts)}</span>
                        )}
                      </div>
                      <div
                        className={`inline-block px-3.5 py-2 rounded-2xl text-sm leading-relaxed ${
                          Agent
                            ? "bg-slate-50 text-slate-800 border border-slate-100 rounded-tl-sm"
                            : "bg-emerald-50 text-emerald-900 border border-emerald-100 rounded-tr-sm"
                        }`}
                      >
                        {t.text}
                      </div>
                    </div>
                  </div>
                );
              })}
          </div>
        )}
      </div>
    </div>
  );
}

function Field({ label, value }: { label: string; value: any }) {
  return (
    <div>
      <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">{label}</div>
      <div className="text-slate-800">{value || <span className="text-slate-400">—</span>}</div>
    </div>
  );
}