import type { ReactNode } from "react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";

export function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("demo@example.com");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  return (
    <AuthCard title="Login">
      <form
        className="space-y-3"
        onSubmit={async (e) => {
          e.preventDefault();
          setErr("");
          try {
            const u = await login(email, password);
            nav(u.role === "admin" ? "/admin" : "/app/dashboard");
          } catch {
            setErr("Invalid email or password.");
          }
        }}
      >
        <input className="input" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" />
        <input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" />
        {err && <p className="text-sm text-red-600">{err}</p>}
        <button className="btn btn-primary w-full">Login</button>
      </form>
      <p className="text-xs text-gray-500 mt-4">
        Demo: demo@example.com / Demo123! · Admin: admin@example.com / Admin123!
      </p>
      <Link to="/forgot-password" className="text-sm text-blue-700 mt-3 inline-block">
        Forgot password
      </Link>
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
  return (
    <AuthCard title="Create account">
      <form
        className="space-y-3"
        onSubmit={async (e) => {
          e.preventDefault();
          try {
            await signup(name, email, password);
            nav("/app/onboarding");
          } catch {
            setErr("Could not sign up.");
          }
        }}
      >
        <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Name" />
        <input className="input" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" />
        <input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" />
        {err && <p className="text-sm text-red-600">{err}</p>}
        <button className="btn btn-primary w-full">Sign up</button>
      </form>
    </AuthCard>
  );
}

export function Forgot() {
  const [email, setEmail] = useState("");
  const [msg, setMsg] = useState("");
  return (
    <AuthCard title="Forgot password">
      <form
        className="space-y-3"
        onSubmit={async (e) => {
          e.preventDefault();
          const { data } = await api.post("/auth/forgot-password", { email });
          setMsg(data.message);
        }}
      >
        <input className="input" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" />
        <button className="btn btn-primary w-full">Submit</button>
      </form>
      {msg && <p className="text-sm text-gray-600 mt-3">{msg}</p>}
    </AuthCard>
  );
}

function AuthCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="card w-full max-w-md p-8 score-glow">
        <div className="flex items-center justify-between">
          <Link to="/" className="text-sm text-blue-800 flex items-center">
            <span className="logo-mark">L</span> Lumina
          </Link>
        </div>
        <h1 className="font-display text-3xl mt-3">{title}</h1>
        <div className="mt-6">{children}</div>
        <p className="text-sm text-gray-500 mt-6">
          <Link to="/login">Login</Link> · <Link to="/signup">Signup</Link>
        </p>
      </div>
    </div>
  );
}
