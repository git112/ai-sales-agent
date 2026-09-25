import type { ReactNode } from "react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";

export function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  return (
    <AuthCard title="Welcome back" subtitle="Sign in to your autonomous sales command center">
      <form
        className="space-y-4"
        onSubmit={async (e) => {
          e.preventDefault();
          setErr("");
          setBusy(true);
          try {
            const u = await login(email, password);
            nav(u.role === "admin" ? "/admin" : "/app/dashboard");
          } catch {
            setErr("Invalid email or password.");
          } finally {
            setBusy(false);
          }
        }}
      >
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">Email address</label>
          <input className="input h-11" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@company.com" required />
        </div>
        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="block text-xs font-semibold text-slate-700">Password</label>
            <Link to="/forgot-password" className="text-xs text-indigo-600 hover:text-indigo-800 font-medium">
              Forgot password?
            </Link>
          </div>
          <input className="input h-11" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" required />
        </div>
        {err && <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 rounded-xl text-xs font-medium">{err}</div>}
        <button className="btn btn-primary w-full h-11 text-sm font-semibold" disabled={busy}>
          {busy ? "Signing in…" : "Sign In"}
        </button>
      </form>
    </AuthCard>
  );
}

export function Signup() {
  const { signup } = useAuth();
  const nav = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  return (
    <AuthCard title="Create account" subtitle="Activate autonomous opportunity discovery & voice calling">
      <form
        className="space-y-4"
        onSubmit={async (e) => {
          e.preventDefault();
          setErr("");
          setBusy(true);
          try {
            await signup(name, email, password);
            nav("/app/onboarding");
          } catch {
            setErr("Could not sign up. Please try again.");
          } finally {
            setBusy(false);
          }
        }}
      >
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">Full Name</label>
          <input className="input h-11" value={name} onChange={(e) => setName(e.target.value)} placeholder="Alex Mercer" required />
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">Work Email</label>
          <input className="input h-11" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@company.com" required />
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">Password</label>
          <input className="input h-11" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" required />
        </div>
        {err && <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 rounded-xl text-xs font-medium">{err}</div>}
        <button className="btn btn-primary w-full h-11 text-sm font-semibold" disabled={busy}>
          {busy ? "Creating account…" : "Create Account"}
        </button>
      </form>
    </AuthCard>
  );
}

export function Forgot() {
  const [email, setEmail] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  return (
    <AuthCard title="Reset password" subtitle="Enter your email to receive recovery instructions">
      <form
        className="space-y-4"
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          try {
            const { data } = await api.post("/auth/forgot-password", { email });
            setMsg(data.message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">Account Email</label>
          <input className="input h-11" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@company.com" required />
        </div>
        <button className="btn btn-primary w-full h-11 text-sm font-semibold" disabled={busy}>
          {busy ? "Submitting…" : "Send Reset Link"}
        </button>
      </form>
      {msg && <p className="text-xs text-emerald-700 bg-emerald-50 border border-emerald-200 p-3 rounded-xl mt-3">{msg}</p>}
    </AuthCard>
  );
}

function AuthCard({ title, subtitle, children }: { title: string; subtitle?: string; children: ReactNode }) {
  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-slate-50/50">
      <div className="card w-full max-w-md p-8 bg-white shadow-md space-y-6">
        <div className="flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5">
            <span className="logo-mark">L</span>
            <span className="font-bold text-slate-900 font-display text-base">Lumina</span>
          </Link>
        </div>

        <div>
          <h1 className="font-display text-2xl font-bold text-slate-900 tracking-tight">{title}</h1>
          {subtitle && <p className="text-xs text-slate-500 mt-1">{subtitle}</p>}
        </div>

        {children}

        <div className="pt-4 border-t border-slate-100 text-center text-xs text-slate-500">
          <Link to="/login" className="text-indigo-600 hover:text-indigo-800 font-medium">
            Sign In
          </Link>
          <span className="mx-2 text-slate-300">·</span>
          <Link to="/signup" className="text-indigo-600 hover:text-indigo-800 font-medium">
            Create Account
          </Link>
        </div>
      </div>
    </div>
  );
}
