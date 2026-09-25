import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  Target,
  Users,
  Megaphone,
  Bot,
  PhoneCall,
  CheckSquare,
  Sparkles,
  BookOpen,
  Radio,
  BarChart3,
  Bell,
  Settings,
  Shield,
  LogOut,
  Compass,
  ArrowRight,
  CalendarCheck2,
} from "lucide-react";
import { api, authStore } from "../api";
import { useAuth } from "../auth";

const navItems = [
  { label: "Dashboard", to: "/app/dashboard", icon: LayoutDashboard },
  { label: "Opportunities", to: "/app/opportunities", icon: Target },
  { label: "Leads", to: "/app/leads", icon: Users },
  { label: "Campaigns", to: "/app/campaigns", icon: Megaphone },
  { label: "Voice Agents", to: "/app/agents", icon: Bot },
  { label: "Calls", to: "/app/calls", icon: PhoneCall },
  { label: "Calendly Tracker", to: "/app/calendly", icon: CalendarCheck2 },
  { label: "Tasks", to: "/app/tasks", icon: CheckSquare },
  { label: "AI Copilot", to: "/app/copilot", icon: Sparkles },
  { label: "Knowledge Base", to: "/app/knowledge", icon: BookOpen },
  { label: "Opportunity Radar", to: "/app/radar", icon: Radio },
  { label: "Analytics", to: "/app/analytics", icon: BarChart3 },
  { label: "Notifications", to: "/app/notifications", icon: Bell },
  { label: "Settings", to: "/app/settings", icon: Settings },
];

export default function AppShell() {
  const { user, logout } = useAuth();
  const navGo = useNavigate();
  const [notes, setNotes] = useState<any[]>([]);

  useEffect(() => {
    api.get("/workspaces").then(({ data }) => {
      const ws = data.find((w: any) => w.id === authStore.workspaceId()) || data[0];
      if (ws) {
        authStore.setWorkspace(ws.id);
      }
    });
    api.get("/notifications").then(({ data }) => setNotes(data.filter((n: any) => !n.read)));
  }, []);

  const unreadCount = notes.filter((n) => !n.read).length;

  return (
    <div className="min-h-screen flex bg-slate-50/50">
      {/* Sidebar */}
      <aside className="w-64 border-r border-slate-200 flex flex-col bg-white shrink-0">
        <div className="p-5 border-b border-slate-100 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3">
            <span className="logo-mark">L</span>
            <div>
              <div className="font-bold text-slate-900 leading-none text-base">Lumina</div>
              <div className="text-[11px] font-medium text-slate-500 mt-1">Autonomous Sales Agent</div>
            </div>
          </Link>
        </div>

        <nav className="p-3 flex-1 space-y-1 overflow-y-auto">
          <div className="px-3 py-1.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
            Workspace
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isNotification = item.to === "/app/notifications";
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center justify-between rounded-xl px-3 py-2 text-sm font-medium transition-all ${
                    isActive
                      ? "bg-indigo-50/90 text-indigo-700 font-semibold shadow-xs"
                      : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                  }`
                }
              >
                <div className="flex items-center gap-2.5">
                  <Icon className="w-4 h-4 text-inherit shrink-0" />
                  <span>{item.label}</span>
                </div>
                {isNotification && unreadCount > 0 && (
                  <span className="bg-indigo-600 text-white text-[11px] font-bold px-1.5 py-0.5 rounded-full min-w-5 text-center">
                    {unreadCount}
                  </span>
                )}
              </NavLink>
            );
          })}

          {user?.role === "admin" && (
            <NavLink
              to="/admin"
              className={({ isActive }) =>
                `flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm font-medium transition-all ${
                  isActive
                    ? "bg-indigo-50 text-indigo-700 font-semibold"
                    : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                }`
              }
            >
              <Shield className="w-4 h-4" />
              <span>Admin Console</span>
            </NavLink>
          )}
        </nav>

        {/* User Card */}
        <div className="p-3 border-t border-slate-100 bg-slate-50/50">
          <div className="flex items-center justify-between p-2 rounded-xl bg-white border border-slate-200/80 shadow-xs">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-8 h-8 rounded-lg bg-indigo-100 text-indigo-700 font-bold flex items-center justify-center text-xs shrink-0">
                {user?.email?.charAt(0).toUpperCase() || "U"}
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-xs font-semibold text-slate-800 truncate">{user?.email || "User"}</div>
                <div className="text-[10px] text-slate-400 capitalize">{user?.role || "Member"}</div>
              </div>
            </div>
            <button
              onClick={async () => {
                await logout();
                navGo("/");
              }}
              title="Log out"
              className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Header */}
        <header className="h-16 border-b border-slate-200 bg-white flex items-center justify-between px-8 sticky top-0 z-10 shadow-xs">
          <div className="flex items-center gap-4 min-w-0">
            {/* Status indicator */}
            <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200/70 text-xs font-medium text-emerald-700">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              Sales Intelligence Engine Active
            </div>

            {unreadCount > 0 && notes[0] && (
              <Link
                to="/app/notifications"
                className="hidden md:flex items-center gap-2 text-xs font-medium text-slate-600 hover:text-indigo-600 bg-slate-50 hover:bg-indigo-50/60 px-3 py-1 rounded-full border border-slate-200 transition"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-500"></span>
                <span className="font-semibold text-slate-800">{unreadCount} new:</span>
                <span className="truncate max-w-[280px]">{notes[0].title}</span>
                <ArrowRight className="w-3 h-3 text-slate-400" />
              </Link>
            )}
          </div>

          <div className="flex items-center gap-3">
            <Link
              to="/app/onboarding"
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-indigo-600 hover:text-indigo-800 bg-indigo-50 hover:bg-indigo-100 rounded-lg border border-indigo-200 transition"
              title="Configure your AI business profile"
            >
              <Compass className="w-3.5 h-3.5 text-indigo-400" />
              <span>Setup Guide</span>
            </Link>

            <Link
              to="/app/notifications"
              className="relative p-2 text-slate-500 hover:text-indigo-600 hover:bg-slate-50 rounded-lg border border-slate-200 transition"
              title="Notifications"
            >
              <Bell className="w-4 h-4" />
              {unreadCount > 0 && (
                <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-indigo-600 ring-2 ring-white"></span>
              )}
            </Link>
          </div>
        </header>

        {/* Page Content */}
        <main className="p-8 flex-1 max-w-7xl w-full mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
