import type { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import Landing from "./pages/Landing";
import { Login, Signup, Forgot } from "./pages/AuthPages";
import AppShell from "./pages/AppShell";
import Dashboard from "./pages/Dashboard";
import Onboarding from "./pages/Onboarding";
import Opportunities from "./pages/Opportunities";
import OpportunityDetail from "./pages/OpportunityDetail";
import Leads from "./pages/Leads";
import LeadDetail from "./pages/LeadDetail";
import ImportLeads from "./pages/ImportLeads";
import Segments from "./pages/Segments";
import Campaigns from "./pages/Campaigns";
import CampaignNew from "./pages/CampaignNew";
import CampaignDetail from "./pages/CampaignDetail";
import Agents from "./pages/Agents";
import AgentDetail from "./pages/AgentDetail";
import Playground from "./pages/Playground";
import Calls from "./pages/Calls";
import CallDetail from "./pages/CallDetail";
import Tasks from "./pages/Tasks";
import Copilot from "./pages/Copilot";
import Knowledge from "./pages/Knowledge";
import Radar from "./pages/Radar";
import Analytics from "./pages/Analytics";
import Settings from "./pages/Settings";
import Admin from "./pages/Admin";
import Docs from "./pages/Docs";
import Notifications from "./pages/Notifications";
import Pricing from "./pages/Pricing";
import Legal from "./pages/Legal";
import CalendlyTracker from "./pages/CalendlyTracker";

function Private({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="p-10 text-gray-500">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function AdminOnly({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="p-10 text-gray-500">Loading…</div>;
  if (user?.role !== "admin") return <Navigate to="/app/dashboard" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/docs" element={<Docs />} />
      <Route path="/pricing" element={<Pricing />} />
      <Route path="/privacy" element={<Legal kind="privacy" />} />
      <Route path="/terms" element={<Legal kind="terms" />} />
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
      <Route path="/forgot-password" element={<Forgot />} />
      <Route
        path="/app"
        element={
          <Private>
            <AppShell />
          </Private>
        }
      >
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="onboarding" element={<Onboarding />} />
        <Route path="opportunities" element={<Opportunities />} />
        <Route path="opportunities/:id" element={<OpportunityDetail />} />
        <Route path="leads" element={<Leads />} />
        <Route path="leads/import" element={<ImportLeads />} />
        <Route path="leads/segments" element={<Segments />} />
        <Route path="leads/:id" element={<LeadDetail />} />
        <Route path="campaigns" element={<Campaigns />} />
        <Route path="campaigns/new" element={<CampaignNew />} />
        <Route path="campaigns/:id" element={<CampaignDetail />} />
        <Route path="agents" element={<Agents />} />
        <Route path="agents/:id" element={<AgentDetail />} />
        <Route path="agents/:id/playground" element={<Playground />} />
        <Route path="calls" element={<Calls />} />
        <Route path="calls/:id" element={<CallDetail />} />
        <Route path="tasks" element={<Tasks />} />
        <Route path="copilot" element={<Copilot />} />
        <Route path="knowledge" element={<Knowledge />} />
        <Route path="radar" element={<Radar />} />
        <Route path="analytics" element={<Analytics />} />
        <Route path="notifications" element={<Notifications />} />
        <Route path="calendly" element={<CalendlyTracker />} />
        <Route path="settings" element={<Settings />} />
      </Route>
      <Route
        path="/admin"
        element={
          <Private>
            <AdminOnly>
              <Admin />
            </AdminOnly>
          </Private>
        }
      />
      <Route
        path="/admin/:tab"
        element={
          <Private>
            <AdminOnly>
              <Admin />
            </AdminOnly>
          </Private>
        }
      />
    </Routes>
  );
}
