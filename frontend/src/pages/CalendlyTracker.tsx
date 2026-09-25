import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  CalendarCheck2, MessageSquare, RefreshCw, Clock,
  CheckCircle2, PhoneCall, ArrowUpRight, Sparkles,
  Send, ExternalLink, Link2, AlertTriangle, KeyRound,
  Globe, ShieldCheck, Zap, Copy, Eye, EyeOff,
  Mail, MailCheck, AlertCircle,
} from "lucide-react";
import { api } from "../api";

const STATUS_META: Record<string, { label: string; color: string; icon: any }> = {
  pending_booking: { label: "Awaiting Booking", color: "bg-amber-50 text-amber-700 border border-amber-200", icon: Clock },
  booked: { label: "Booked", color: "bg-emerald-50 text-emerald-700 border border-emerald-200", icon: CheckCircle2 },
  recalled: { label: "Re-dialed", color: "bg-indigo-50 text-indigo-700 border border-indigo-200", icon: PhoneCall },
};

const DELIVERY_META: Record<string, { label: string; color: string; icon: any }> = {
  calendly_email: { label: "Calendly Email Sent", color: "bg-emerald-50 text-emerald-700 border-emerald-200", icon: MailCheck },
  simulated_sms:  { label: "SMS Link Sent", color: "bg-amber-50 text-amber-700 border-amber-200", icon: MessageSquare },
  skipped:         { label: "No Channel", color: "bg-slate-100 text-slate-600 border-slate-200", icon: AlertCircle },
  twilio:          { label: "Twilio SMS", color: "bg-violet-50 text-violet-700 border-violet-200", icon: MessageSquare },
};

const PREFERRED_SLOTS = [
  { id: "slot_today_2pm", title: "Today 2:00 PM - 2:30 PM", specialist: "Sarah Jenkins" },
  { id: "slot_today_430pm", title: "Today 4:30 PM - 5:00 PM", specialist: "David Chen" },
  { id: "slot_tomorrow_10am", title: "Tomorrow 10:00 AM - 10:30 AM", specialist: "Sarah Jenkins" },
  { id: "slot_tomorrow_2pm", title: "Tomorrow 2:00 PM - 2:30 PM", specialist: "Elena Rostova" },
  { id: "slot_mon_11am", title: "Monday 11:00 AM - 11:30 AM", specialist: "David Chen" },
];

interface Booking {
  id: string; lead_id: string; company?: string; contact_name?: string;
  contact_email?: string; lead_email_original?: string;
  phone?: string; calendly_link?: string; status: string; created_at: string;
  booked_at?: string; recalled_at?: string;
  delivery_channel?: string; calendly_event_uri?: string;
  requested_slot?: { label?: string; date?: string; time?: string; specialist?: string };
  booking_details?: { timeslot?: string; specialist?: string };
  recall_call_id?: string;
}

export default function CalendlyTracker() {
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [leads, setLeads] = useState<any[]>([]);
  const [smsSent, setSmsSent] = useState<string[]>([]);
  const [selectedBooking, setSelectedBooking] = useState<Booking | null>(null);
  const [bookSlot, setBookSlot] = useState("");
  const [recallRunning, setRecallRunning] = useState(false);
  const [bookingBusy, setBookingBusy] = useState("");
  const [smsBusy, setSmsBusy] = useState("");
  const [recallResult, setRecallResult] = useState<any>(null);
  const [scheduleTime, setScheduleTime] = useState<Record<string, string>>({});
  const [scheduleBusy, setScheduleBusy] = useState<string>("");
  const [scheduleResult, setScheduleResult] = useState<any>(null);
  const [calendlyConfig, setCalendlyConfig] = useState<any>(null);

  // Calendly Connect panel state
  const [showConnect, setShowConnect] = useState(false);
  const [pat, setPat] = useState("");
  const [webhookUrl, setWebhookUrl] = useState("");
  const [showPat, setShowPat] = useState(false);
  const [registerBusy, setRegisterBusy] = useState(false);
  const [registerResult, setRegisterResult] = useState<any>(null);

  const load = async () => {
    const [bRes, lRes, cfgRes] = await Promise.all([
      api.get("/calendly/bookings"),
      api.get("/leads"),
      api.get("/calendly/config").catch(() => ({ data: {} })),
    ]);
    setBookings(bRes.data);
    setLeads(lRes.data);
    setCalendlyConfig(cfgRes.data);
  };

  useEffect(() => { load(); }, []);

  const pending = bookings.filter((b) => b.status === "pending_booking");
  const booked = bookings.filter((b) => b.status === "booked");
  const recalled = bookings.filter((b) => b.status === "recalled");

  const CALENDLY_BOOKING_URL = calendlyConfig?.booking_url || "https://calendly.com/nanditkalaria27/30min";

  async function sendCalendlySms(leadId: string) {
    setSmsBusy(leadId);
    try {
      const lead = leads.find((l) => l.id === leadId);
      await api.post("/calendly/send-sms", { lead_id: leadId, phone: lead?.phone });
      setSmsSent((prev) => [...prev, leadId]);
      await load();
    } finally { setSmsBusy(""); }
  }

  async function confirmBooking(booking: Booking, slotId: string) {
    setBookingBusy(booking.id);
    try {
      const slot = PREFERRED_SLOTS.find((s) => s.id === slotId);
      await api.post("/calendly/book", {
        booking_id: booking.id, lead_id: booking.lead_id,
        slot_id: slotId, slot_title: slot?.title, specialist: slot?.specialist, notes: "",
      });
      setSelectedBooking(null); setBookSlot(""); await load();
    } finally { setBookingBusy(""); }
  }

  async function runTrackAndRecall() {
    setRecallRunning(true); setRecallResult(null);
    try {
      const { data } = await api.post("/calendly/track-and-recall", { force_immediate: true });
      setRecallResult(data); await load();
    } finally { setRecallRunning(false); }
  }

  async function scheduleViaEmail(leadId: string) {
    const text = (scheduleTime[leadId] || "").trim();
    if (!text) return;
    setScheduleBusy(leadId);
    try {
      const { data } = await api.post("/calendly/schedule-callback", {
        lead_id: leadId, time_text: text,
      });
      setScheduleResult({ leadId, ...data });
      setScheduleTime((p) => ({ ...p, [leadId]: "" }));
      await load();
    } catch (e: any) {
      setScheduleResult({
        leadId, ok: false,
        error: e?.response?.data?.detail || "Failed to schedule",
      });
    } finally { setScheduleBusy(""); }
  }

  async function registerWebhook() {
    setRegisterBusy(true); setRegisterResult(null);
    try {
      const { data } = await api.post("/calendly/register-webhook", {
        pat: pat || undefined,
        webhook_url: webhookUrl || undefined,
      });
      setRegisterResult(data);
    } catch (e: any) {
      setRegisterResult({ ok: false, error: e?.response?.data?.detail || "Request failed" });
    } finally { setRegisterBusy(false); }
  }

  function copyText(text: string) {
    navigator.clipboard.writeText(text).catch(() => {});
  }

  const leadsWithoutSms = leads.filter((l) => !bookings.find((b) => b.lead_id === l.id)).slice(0, 5);
  const emailScheduled = bookings.filter((b) => b.delivery_channel === "calendly_email");

  function DeliveryChip({ channel }: { channel?: string }) {
    const meta = DELIVERY_META[channel || ""] || DELIVERY_META["simulated_sms"];
    const Icon = meta.icon;
    return (
      <span className={`badge ${meta.color} border text-xs flex items-center gap-1`}>
        <Icon className="w-3 h-3" />
        {meta.label}
      </span>
    );
  }

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-violet-50 text-violet-600 border border-violet-100">
              <CalendarCheck2 className="w-5 h-5" />
            </div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Calendly Booking Tracker</h1>
            <span className="badge bg-violet-50 text-violet-700 border border-violet-200 ml-1">SMS + Auto-Recall</span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            AI detects human-handoff intent during calls and texts a tracked Calendly link. Unbooked leads are auto re-dialed.
          </p>
        </div>
        <button
          id="btn-connect-calendly"
          className="btn btn-ghost flex items-center gap-2 shrink-0 border border-violet-200 text-violet-700 hover:bg-violet-50"
          onClick={() => setShowConnect((v) => !v)}
        >
          <Link2 className="w-4 h-4" />
          {showConnect ? "Hide Setup" : "Connect Calendly"}
        </button>
      </div>

      {/* ── Calendly Connect / Webhook Setup Panel ── */}
      {showConnect && (
        <div className="card bg-white shadow-xs border border-violet-200 overflow-hidden">
          <div className="p-4 border-b border-violet-100 bg-violet-50/50 flex items-center gap-2">
            <Link2 className="w-4 h-4 text-violet-600" />
            <h2 className="font-bold text-slate-900">Connect Calendly Webhook</h2>
            <span className="ml-auto badge bg-white text-violet-700 border border-violet-200 text-xs">One-time setup</span>
          </div>

          <div className="p-5 space-y-5">
            {/* Option A — OAuth (recommended) */}
            <div className="p-4 rounded-xl bg-violet-50 border border-violet-200">
              <div className="flex items-start gap-3">
                <div className="p-2 bg-violet-100 rounded-lg shrink-0">
                  <Zap className="w-4 h-4 text-violet-600" />
                </div>
                <div className="flex-1">
                  <div className="font-semibold text-violet-900 text-sm">Option A — Connect via OAuth (Recommended)</div>
                  <p className="text-xs text-violet-700 mt-0.5 mb-2">
                    One click. Calendly grants all required scopes automatically including <code className="bg-violet-100 px-1 rounded">scheduled_events:read</code>.
                    Webhook is registered and signing key saved instantly.
                  </p>
                  <div className="text-xs text-violet-600 mb-3">
                    First, create an OAuth app at{" "}
                    <a href="https://developer.calendly.com" target="_blank" rel="noreferrer" className="underline font-semibold">developer.calendly.com</a>
                    {" "}with redirect URI: <code className="bg-violet-100 px-1 rounded">http://localhost:8000/api/v1/calendly/oauth/callback</code>
                    {" "}then set <code className="bg-violet-100 px-1 rounded">CALENDLY_CLIENT_ID</code> and{" "}
                    <code className="bg-violet-100 px-1 rounded">CALENDLY_CLIENT_SECRET</code> in .env.
                  </div>
                  <a
                    id="btn-oauth-connect"
                    href="http://localhost:8000/api/v1/calendly/oauth/start"
                    target="_blank"
                    rel="noreferrer"
                    className="btn btn-primary inline-flex items-center gap-2 text-sm"
                  >
                    <Link2 className="w-4 h-4" />
                    Connect Calendly via OAuth
                  </a>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3 text-xs text-slate-400">
              <div className="flex-1 border-t border-slate-200" />
              <span>OR use PAT (limited scopes)</span>
              <div className="flex-1 border-t border-slate-200" />
            </div>

            {/* Option B — PAT warning */}
            <div className="p-4 rounded-xl bg-amber-50 border border-amber-200">
              <div className="flex items-start gap-2.5">
                <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                <div>
                  <div className="font-semibold text-amber-800 text-sm">Option B — PAT (requires extra scope)</div>
                  <p className="text-xs text-amber-700 mt-0.5">
                    Calendly's PAT generator at <code className="bg-amber-100 px-1 rounded">calendly.com/integrations/api_webhooks</code> only grants{" "}
                    <code className="bg-amber-100 px-1 rounded">webhooks:read webhooks:write</code>.
                    The webhook also needs <code className="bg-amber-100 px-1 rounded">scheduled_events:read</code> — which is only available via OAuth above.
                  </p>
                </div>
              </div>
            </div>

            {/* Step 2 — PAT input */}
            <div className="space-y-3">
              <div>
                <label className="text-xs font-semibold text-slate-700 mb-1 block flex items-center gap-1">
                  <KeyRound className="w-3.5 h-3.5 text-violet-500" />
                  Calendly Personal Access Token (PAT)
                </label>
                <div className="relative">
                  <input
                    id="input-calendly-pat"
                    type={showPat ? "text" : "password"}
                    className="input pr-10 font-mono text-xs"
                    placeholder="eyJraWQiOiI..."
                    value={pat}
                    onChange={(e) => setPat(e.target.value)}
                  />
                  <button
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                    onClick={() => setShowPat((v) => !v)}
                    type="button"
                  >
                    {showPat ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700 mb-1 block flex items-center gap-1">
                  <Globe className="w-3.5 h-3.5 text-violet-500" />
                  Public API URL <span className="text-slate-400 font-normal">(where Calendly sends events)</span>
                </label>
                <input
                  id="input-webhook-url"
                  type="text"
                  className="input font-mono text-xs"
                  placeholder="https://your-api-host.com  (or ngrok URL for local testing)"
                  value={webhookUrl}
                  onChange={(e) => setWebhookUrl(e.target.value)}
                />
                <p className="text-[11px] text-slate-400 mt-1">
                  Webhooks require a public HTTPS URL. For local testing use{" "}
                  <a href="https://ngrok.com" target="_blank" rel="noreferrer" className="underline">ngrok</a>:{" "}
                  <code className="bg-slate-100 px-1 rounded">ngrok http 8000</code> then paste the https URL here.
                </p>
              </div>

              <button
                id="btn-register-webhook"
                className="btn btn-primary flex items-center gap-2"
                disabled={registerBusy || !pat}
                onClick={registerWebhook}
              >
                <Zap className={`w-4 h-4 ${registerBusy ? "animate-pulse" : ""}`} />
                {registerBusy ? "Registering..." : "Register Webhook with Calendly"}
              </button>
            </div>

            {/* Result */}
            {registerResult && (
              <div className={`p-4 rounded-xl border text-sm ${
                registerResult.ok
                  ? "bg-emerald-50 border-emerald-200"
                  : "bg-rose-50 border-rose-200"
              }`}>
                {registerResult.ok ? (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 font-semibold text-emerald-800">
                      <ShieldCheck className="w-4 h-4" />
                      Webhook Registered Successfully!
                    </div>
                    <div className="text-xs text-emerald-700 space-y-1">
                      <div>Calendly will now send events to: <code className="bg-emerald-100 px-1 rounded">{registerResult.webhook_url}</code></div>
                      <div>Events: {(registerResult.events || []).join(", ")}</div>
                    </div>
                    {registerResult.signing_key && (
                      <div className="mt-2 p-3 bg-white rounded-lg border border-emerald-200">
                        <div className="text-xs font-semibold text-slate-700 mb-1 flex items-center gap-1">
                          <KeyRound className="w-3 h-3 text-emerald-600" />
                          Signing Key {registerResult.signing_key_saved_to_env ? "(auto-saved to .env)" : "(copy to .env as CALENDLY_WEBHOOK_SECRET)"}
                        </div>
                        <div className="flex items-center gap-2">
                          <code className="text-[11px] text-slate-700 break-all flex-1">{registerResult.signing_key}</code>
                          <button
                            className="btn btn-ghost h-7 px-2 shrink-0"
                            onClick={() => copyText(registerResult.signing_key)}
                            title="Copy"
                          >
                            <Copy className="w-3.5 h-3.5" />
                          </button>
                        </div>
                        {!registerResult.signing_key_saved_to_env && (
                          <div className="mt-1.5 text-[11px] text-slate-500">
                            Add to your <code>.env</code>: <code className="bg-slate-100 px-1 rounded">CALENDLY_WEBHOOK_SECRET={registerResult.signing_key}</code>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 font-semibold text-rose-800">
                      <AlertTriangle className="w-4 h-4" />
                      {registerResult.error === "insufficient_scopes" ? "PAT Missing Required Scopes" : "Registration Failed"}
                    </div>
                    {registerResult.missing_scopes?.length > 0 && (
                      <div className="text-xs text-rose-700">
                        Missing: {registerResult.missing_scopes.map((s: string) => (
                          <code key={s} className="bg-rose-100 px-1 rounded mx-0.5">{s}</code>
                        ))}
                      </div>
                    )}
                    {registerResult.action_required && (
                      <div className="text-xs text-rose-700 mt-1">{registerResult.action_required}</div>
                    )}
                    {registerResult.error && registerResult.error !== "insufficient_scopes" && (
                      <div className="text-xs text-rose-700">{registerResult.error}</div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Flow diagram */}
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs text-slate-600">
              <div className="font-semibold text-slate-700 mb-2 flex items-center gap-1">
                <Zap className="w-3.5 h-3.5 text-violet-500" />
                How the webhook works once registered:
              </div>
              <div className="flex flex-wrap gap-2 items-center">
                {[
                  "Lead books via Calendly link",
                  "Calendly fires invitee.created",
                  "Our webhook receives it",
                  "Booking auto-confirmed in CRM",
                  "Task + notification created",
                  "No more AI re-dial needed",
                ].map((step, i, arr) => (
                  <span key={i} className="flex items-center gap-1">
                    <span className="bg-violet-100 text-violet-700 px-2 py-0.5 rounded-full">{step}</span>
                    {i < arr.length - 1 && <span className="text-slate-300">→</span>}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Awaiting Booking", count: pending.length, bg: "bg-amber-50", text: "text-amber-700", border: "border-l-amber-500", icon: Clock },
          { label: "Confirmed", count: booked.length, bg: "bg-emerald-50", text: "text-emerald-700", border: "border-l-emerald-500", icon: CheckCircle2 },
          { label: "Calendly Email Sent", count: emailScheduled.length, bg: "bg-emerald-50", text: "text-emerald-700", border: "border-l-emerald-500", icon: MailCheck },
          { label: "Auto Re-dialed", count: recalled.length, bg: "bg-indigo-50", text: "text-indigo-700", border: "border-l-indigo-500", icon: PhoneCall },
        ].map(({ label, count, bg, text, border, icon: Icon }) => (
          <div key={label} className={`card p-4 bg-white shadow-xs flex items-center gap-3 border-l-4 ${border}`}>
            <div className={`p-2.5 rounded-xl ${bg} ${text} shrink-0`}><Icon className="w-5 h-5" /></div>
            <div>
              <div className={`text-2xl font-bold ${text}`}>{count}</div>
              <div className="text-xs text-slate-500 font-medium">{label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* ── Scheduled Meetings (Calendly Email) ───────────────── */}
      {emailScheduled.length > 0 && (
        <div className="card bg-white shadow-xs overflow-hidden border-l-4 border-l-emerald-500">
          <div className="p-4 border-b border-emerald-100 bg-emerald-50/40 flex items-center gap-2">
            <Mail className="w-4 h-4 text-emerald-600" />
            <h2 className="font-bold text-slate-900">Scheduled Meetings — Calendly Email</h2>
            <span className="ml-auto badge bg-emerald-50 text-emerald-700 border border-emerald-200">
              {emailScheduled.length} email{emailScheduled.length !== 1 ? "s" : ""} sent
            </span>
          </div>
          <div className="divide-y divide-slate-100">
            {emailScheduled.map((b) => (
              <div key={b.id} className="p-4 flex flex-col sm:flex-row sm:items-center gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-semibold text-slate-900 text-sm">
                      {b.company || b.contact_name || b.lead_id}
                    </span>
                    <DeliveryChip channel={b.delivery_channel} />
                  </div>
                  {b.requested_slot && (
                    <div className="text-xs text-slate-700 mt-1">
                      📅 <span className="font-medium">{b.requested_slot.label}</span>
                      {b.requested_slot.specialist && (
                        <span className="text-slate-500"> · with {b.requested_slot.specialist}</span>
                      )}
                    </div>
                  )}
                  <div className="text-xs text-slate-500 mt-1 flex items-center gap-1 flex-wrap">
                      <Mail className="w-3 h-3" />
                      Confirmation sent to{" "}
                      <span className="font-mono text-slate-700">{b.contact_email}</span>
                      {b.lead_email_original && b.lead_email_original !== b.contact_email && (
                        <span className="text-slate-400">
                          (lead email: <span className="font-mono">{b.lead_email_original}</span>)
                        </span>
                      )}
                    </div>
                  {b.calendly_event_uri && (
                    <a href={b.calendly_event_uri} target="_blank" rel="noreferrer"
                      className="text-[11px] text-indigo-600 hover:underline mt-1 inline-flex items-center gap-1">
                      <ExternalLink className="w-3 h-3" /> {b.calendly_event_uri}
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Schedule-via-Email result banner */}
      {scheduleResult && (
        <div className={`p-3 rounded-xl border text-sm flex items-start gap-2 ${
          scheduleResult.ok
            ? "bg-emerald-50 border-emerald-200"
            : "bg-rose-50 border-rose-200"
        }`}>
          {scheduleResult.ok ? <MailCheck className="w-4 h-4 text-emerald-600 mt-0.5" /> : <AlertCircle className="w-4 h-4 text-rose-600 mt-0.5" />}
          <div className="flex-1 text-xs">
            <div className="font-semibold text-slate-900">
              {scheduleResult.ok
                ? `Calendly event created · ${scheduleResult.parsed?.label}`
                : `Failed: ${scheduleResult.error}`}
            </div>
            {scheduleResult.ok && (
              <div className="text-slate-600 mt-0.5">
                Delivery: {scheduleResult.delivery_channel} ·
                Email to: <span className="font-mono">{scheduleResult.email}</span>
                {scheduleResult.email_overridden && (
                  <span className="text-slate-400 text-xs">
                    {" "}(lead email was overridden)
                  </span>
                )}
                {scheduleResult.calendly_event_uri && (
                  <> · <a href={scheduleResult.calendly_event_uri} target="_blank" rel="noreferrer" className="underline">view event</a></>
                )}
              </div>
            )}
          </div>
          <button className="text-slate-400 hover:text-slate-700" onClick={() => setScheduleResult(null)}>×</button>
        </div>
      )}

      {/* Calendly Link Preview */}
      <div className="card p-4 bg-white shadow-xs border border-violet-100 flex flex-col sm:flex-row sm:items-center gap-3">
        <div className="flex-1 min-w-0">
          <div className="text-xs font-semibold text-slate-500 mb-1">Active Calendly Booking Link</div>
          <div className="flex items-center gap-2">
            <CalendarCheck2 className="w-4 h-4 text-violet-500 shrink-0" />
            <a
              href={CALENDLY_BOOKING_URL}
              target="_blank"
              rel="noreferrer"
              className="text-sm text-violet-700 hover:underline font-medium truncate"
            >
              {CALENDLY_BOOKING_URL}
            </a>
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">
            Lead-tracked links are sent as: <code className="bg-slate-100 px-1 rounded">{CALENDLY_BOOKING_URL}?lead_id=...&booking_ref=...&utm_content=...</code>
          </div>
        </div>
        <a
          href={CALENDLY_BOOKING_URL}
          target="_blank"
          rel="noreferrer"
          className="btn btn-ghost shrink-0 flex items-center gap-1.5 text-xs"
        >
          <ExternalLink className="w-3.5 h-3.5" /> Open Calendly
        </a>
      </div>

      {/* Auto Recall Engine */}
      <div className="card p-5 bg-white shadow-xs border border-violet-100">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h2 className="font-bold text-slate-900 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-violet-500" />
              AI Auto Track &amp; Recall Engine
            </h2>
            <p className="text-sm text-slate-500 mt-0.5">
              Checks all unbooked Calendly links and immediately triggers an AI re-dial for each lead.
            </p>
          </div>
          <button
            id="btn-track-recall"
            className="btn btn-primary flex items-center gap-2 shrink-0"
            disabled={recallRunning}
            onClick={runTrackAndRecall}
          >
            <RefreshCw className={`w-4 h-4 ${recallRunning ? "animate-spin" : ""}`} />
            {recallRunning ? "Running..." : "Run Track & Recall"}
          </button>
        </div>
        {recallResult && (
          <div className="mt-4 p-3 rounded-xl bg-indigo-50 border border-indigo-200 text-sm">
            {recallResult.recalls_executed === 0 ? (
              <div className="flex items-center gap-2 text-slate-700">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                No unbooked leads — all Calendly links have been actioned.
              </div>
            ) : (
              <div>
                <div className="font-semibold text-indigo-800 mb-2 flex items-center gap-1.5">
                  <PhoneCall className="w-4 h-4" />
                  {recallResult.recalls_executed} lead{recallResult.recalls_executed !== 1 ? "s" : ""} re-dialed
                </div>
                <div className="space-y-1.5">
                  {(recallResult.recalls || []).map((r: any) => (
                    <div key={r.lead_id} className="flex items-center gap-2 text-xs text-indigo-700">
                      <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 shrink-0" />
                      <span className="font-semibold">{r.company}</span> — {r.message}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Pending Bookings */}
      <div className="card bg-white shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex items-center gap-2">
          <Clock className="w-4 h-4 text-amber-500" />
          <h2 className="font-bold text-slate-900">Awaiting Booking</h2>
          {pending.length > 0 && (
            <span className="ml-auto badge bg-amber-50 text-amber-700 border border-amber-200">{pending.length} unbooked</span>
          )}
        </div>
        {pending.length === 0 ? (
          <div className="p-8 text-center text-slate-400 text-sm">
            <CheckCircle2 className="w-8 h-8 text-emerald-300 mx-auto mb-2" />
            No pending bookings — all Calendly links have been actioned!
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {pending.map((b) => {
              const Meta = STATUS_META[b.status] || STATUS_META["pending_booking"];
              const StatusIcon = Meta.icon;
              return (
                <div key={b.id} className="p-4 flex flex-col sm:flex-row sm:items-center gap-3 hover:bg-slate-50/60 transition-colors">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-semibold text-slate-900 text-sm truncate">{b.company || b.contact_name || b.lead_id}</span>
                      <DeliveryChip channel={b.delivery_channel} />
                    </div>
                    {b.requested_slot?.label && (
                      <div className="text-xs text-slate-700 mt-1">
                        📅 <span className="font-medium">{b.requested_slot.label}</span>
                        {b.requested_slot.specialist && <span className="text-slate-500"> · {b.requested_slot.specialist}</span>}
                      </div>
                    )}
                    <div className="text-xs text-slate-500 mt-0.5 flex items-center gap-2 flex-wrap">
                      <span>{b.phone || "—"}</span>
                      {b.contact_email && (
                        <span className="flex items-center gap-1">
                          · <Mail className="w-3 h-3" />
                          <span className="font-mono">{b.contact_email}</span>
                          {b.lead_email_original && b.lead_email_original !== b.contact_email && (
                            <span className="text-slate-400"> (orig: <span className="font-mono">{b.lead_email_original}</span>)</span>
                          )}
                        </span>
                      )}
                      <span>· {b.created_at?.slice(0, 16).replace("T", " ")} UTC</span>
                    </div>
                    {b.calendly_link && (
                      <a href={b.calendly_link} target="_blank" rel="noreferrer"
                        className="text-xs text-indigo-600 hover:underline mt-0.5 flex items-center gap-1">
                        <ExternalLink className="w-3 h-3" />{b.calendly_link.slice(0, 70)}...
                      </a>
                    )}
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className={`badge text-xs ${Meta.color} flex items-center gap-1`}>
                      <StatusIcon className="w-3 h-3" />{Meta.label}
                    </span>
                    {selectedBooking?.id === b.id ? (
                      <div className="flex items-center gap-2">
                        <select id={`slot-select-${b.id}`} className="input h-8 text-xs max-w-[200px]"
                          value={bookSlot} onChange={(e) => setBookSlot(e.target.value)}>
                          <option value="">-- Pick a slot --</option>
                          {PREFERRED_SLOTS.map((s) => <option key={s.id} value={s.id}>{s.title}</option>)}
                        </select>
                        <button id={`btn-confirm-book-${b.id}`}
                          className="btn btn-primary h-8 px-3 text-xs"
                          disabled={!bookSlot || bookingBusy === b.id}
                          onClick={() => confirmBooking(b, bookSlot)}>
                          {bookingBusy === b.id ? "Saving..." : "Confirm"}
                        </button>
                        <button className="btn btn-ghost h-8 px-2 text-xs"
                          onClick={() => { setSelectedBooking(null); setBookSlot(""); }}>
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <button id={`btn-book-${b.id}`}
                        className="btn btn-ghost h-8 px-3 text-xs flex items-center gap-1"
                        onClick={() => { setSelectedBooking(b); setBookSlot(""); }}>
                        <CalendarCheck2 className="w-3.5 h-3.5" />Mark Booked
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Confirmed Bookings */}
      {booked.length > 0 && (
        <div className="card bg-white shadow-xs overflow-hidden">
          <div className="p-4 border-b border-slate-100 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
            <h2 className="font-bold text-slate-900">Confirmed Bookings</h2>
            <span className="ml-auto badge bg-emerald-50 text-emerald-700 border border-emerald-200">{booked.length} confirmed</span>
          </div>
          <div className="divide-y divide-slate-100">
            {booked.map((b) => (
              <div key={b.id} className="p-4 flex flex-col sm:flex-row sm:items-center gap-3">
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-slate-900 text-sm">{b.company || b.contact_name || b.lead_id}</div>
                  <div className="text-xs text-slate-500 mt-0.5">
                    {b.booking_details?.timeslot || "—"} with {b.booking_details?.specialist || "Specialist"}
                  </div>
                  <div className="text-xs text-slate-400 mt-0.5">
                    Booked: {b.booked_at?.slice(0, 16).replace("T", " ")} UTC
                  </div>
                </div>
                <span className="badge bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3" />Booked
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Re-dialed */}
      {recalled.length > 0 && (
        <div className="card bg-white shadow-xs overflow-hidden">
          <div className="p-4 border-b border-slate-100 flex items-center gap-2">
            <PhoneCall className="w-4 h-4 text-indigo-500" />
            <h2 className="font-bold text-slate-900">Auto Re-dialed Leads</h2>
            <span className="ml-auto badge bg-indigo-50 text-indigo-700 border border-indigo-200">{recalled.length} re-called</span>
          </div>
          <div className="divide-y divide-slate-100">
            {recalled.map((b) => (
              <div key={b.id} className="p-4 flex flex-col sm:flex-row sm:items-center gap-3">
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-slate-900 text-sm">{b.company || b.contact_name || b.lead_id}</div>
                  <div className="text-xs text-slate-500 mt-0.5">Re-dialed: {b.recalled_at?.slice(0, 16).replace("T", " ")} UTC</div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="badge bg-indigo-50 text-indigo-700 border border-indigo-200 text-xs flex items-center gap-1">
                    <PhoneCall className="w-3 h-3" />Re-dialed
                  </span>
                  {b.recall_call_id && (
                    <Link to={`/app/calls/${b.recall_call_id}`}
                      className="text-xs text-indigo-600 hover:underline flex items-center gap-1">
                      View Call <ArrowUpRight className="w-3 h-3" />
                    </Link>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Manual SMS Dispatch + Schedule via Calendly Email */}
      {leadsWithoutSms.length > 0 && (
        <div className="card bg-white shadow-xs overflow-hidden">
          <div className="p-4 border-b border-slate-100 flex items-center gap-2">
            <Send className="w-4 h-4 text-violet-500" />
            <h2 className="font-bold text-slate-900">Send Calendly Link to Lead</h2>
            <span className="ml-auto text-xs text-slate-400">Manual dispatch</span>
          </div>
          <div className="divide-y divide-slate-100">
            {leadsWithoutSms.map((lead) => (
              <div key={lead.id} className="p-4 flex flex-col gap-3">
                <div className="flex items-center justify-between gap-3 flex-wrap">
                  <div className="min-w-0">
                    <div className="font-semibold text-slate-900 text-sm truncate">{lead.company || lead.name}</div>
                    <div className="text-xs text-slate-500">
                      {lead.phone || "No phone"} ·{" "}
                      <span className="font-mono">{lead.email || "—"}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {smsSent.includes(lead.id) ? (
                      <span className="badge bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3" />SMS Sent
                      </span>
                    ) : (
                      <button id={`btn-sms-${lead.id}`}
                        className="btn btn-ghost h-8 px-3 text-xs flex items-center gap-1"
                        disabled={smsBusy === lead.id}
                        onClick={() => sendCalendlySms(lead.id)}>
                        <MessageSquare className="w-3.5 h-3.5 text-violet-500" />
                        {smsBusy === lead.id ? "Sending..." : "Send SMS link"}
                      </button>
                    )}
                  </div>
                </div>
                {/* Schedule via Calendly email */}
                <div className="flex items-center gap-2 flex-wrap">
                  <input
                    id={`input-schedule-${lead.id}`}
                    placeholder="e.g. tomorrow at 11 am"
                    className="input h-8 text-xs flex-1 min-w-[180px] max-w-xs"
                    value={scheduleTime[lead.id] || ""}
                    onChange={(e) => setScheduleTime((p) => ({ ...p, [lead.id]: e.target.value }))}
                  />
                  <button
                    id={`btn-schedule-${lead.id}`}
                    className="btn btn-primary h-8 px-3 text-xs flex items-center gap-1"
                    disabled={scheduleBusy === lead.id || !(scheduleTime[lead.id] || "").trim()}
                    onClick={() => scheduleViaEmail(lead.id)}
                  >
                    <MailCheck className="w-3.5 h-3.5" />
                    {scheduleBusy === lead.id ? "Scheduling..." : "Schedule via Calendly Email"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* How It Works */}
      <div className="card p-5 bg-gradient-to-br from-violet-50 via-indigo-50 to-white border border-violet-100 shadow-xs">
        <h3 className="font-bold text-slate-900 text-sm mb-3 flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-violet-500" />
          Complete Calendly Handoff Flow
        </h3>
        <ol className="space-y-2.5 text-sm text-slate-700">
          {[
            "Lead says 'speak to a human' during an AI call",
            "AI responds with handoff script + automatically texts a tracked Calendly link to the lead's phone",
            "SMS link includes lead_id, booking_ref, utm_source/utm_content tracking params and a redirect_uri",
            "Lead opens link, picks a timeslot on Calendly, and books",
            "Calendly fires invitee.created webhook → booking auto-confirmed in CRM, task + notification created",
            "If lead does NOT book: AI auto re-dials with a follow-up recall script",
            "If lead cancels: invitee.canceled webhook reverts status to pending → triggers another re-dial cycle",
          ].map((text, i) => (
            <li key={i} className="flex items-start gap-2.5">
              <span className="w-5 h-5 rounded-full bg-violet-600 text-white text-[10px] font-bold flex items-center justify-center shrink-0 mt-0.5">
                {i + 1}
              </span>
              <span>{text}</span>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}

