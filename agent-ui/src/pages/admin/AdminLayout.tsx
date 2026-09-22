import {
  Activity,
  BarChart3,
  BookOpen,
  Bot,
  ChevronDown,
  Cpu,
  FileText,
  Gauge,
  LayoutDashboard,
  LogOut,
  Menu,
  MessageSquare,
  ScrollText,
  TrendingUp,
  Users,
  Webhook,
  Workflow,
  Wrench,
  X,
} from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import ThemeToggle from "../../components/ui/ThemeToggle";

interface NavItem {
  label: string;
  path: string;
  icon: typeof LayoutDashboard;
}

interface NavSection {
  id: string;
  label: string;
  items: NavItem[];
}

const sections: NavSection[] = [
  {
    id: "overview",
    label: "Dashboard",
    items: [
      { label: "Overview", path: "/admin", icon: LayoutDashboard },
      // Admins reach the chat workspace with the same session — no second
      // sign-in. The sidebar link is the documented "Chat" entry.
      { label: "Chat", path: "/chat", icon: MessageSquare },
    ],
  },
  {
    id: "ai",
    label: "AI",
    items: [
      { label: "Models", path: "/admin/models", icon: Cpu },
      { label: "Model Routing", path: "/admin/routing", icon: Workflow },
      { label: "Prompt Management", path: "/admin/prompts", icon: FileText },
      { label: "Tool Configuration", path: "/admin/tools", icon: Wrench },
    ],
  },
  {
    id: "knowledge",
    label: "Knowledge",
    items: [
      { label: "Knowledge Base", path: "/admin/knowledge-base", icon: BookOpen },
    ],
  },
  {
    id: "users",
    label: "Users",
    items: [
      { label: "Users", path: "/admin/users", icon: Users },
      { label: "Usage Analytics", path: "/admin/analytics", icon: TrendingUp },
      { label: "Usage Allowance", path: "/admin/usage", icon: BarChart3 },
    ],
  },
  {
    id: "monitoring",
    label: "Monitoring",
    items: [
      { label: "Agent Activity", path: "/admin/activity", icon: Activity },
      { label: "Audit Logs", path: "/admin/audit-logs", icon: ScrollText },
      { label: "API Usage", path: "/admin/api-usage", icon: Webhook },
      { label: "Rate Limiting", path: "/admin/rate-limits", icon: Gauge },
    ],
  },
];

export default function AdminLayout() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const toggleSection = (id: string) =>
    setCollapsed((current) => ({ ...current, [id]: !current[id] }));

  const handleLogout = () => {
    logout();
    // One auth flow: clearing the session lets the route guards send the user
    // to the single login page.
    navigate("/login");
  };

  return (
    <div className="admin-shell">
      <aside className={`admin-nav${menuOpen ? " open" : ""}`}>
        <div className="admin-nav-top">
          <div className="login-brand">
            <Bot size={20} />
            <div>
              <strong>AI Agent</strong>
              <small>Admin Console</small>
            </div>
          </div>
          <button
            type="button"
            className="nav-close"
            onClick={() => setMenuOpen(false)}
            aria-label="Close navigation"
          >
            <X size={17} />
          </button>
        </div>
        <nav>
          {sections.map((section) => {
            const isCollapsed = collapsed[section.id];
            return (
              <div className="nav-section" key={section.id}>
                <button
                  type="button"
                  className={`nav-section-label${isCollapsed ? " collapsed" : ""}`}
                  onClick={() => toggleSection(section.id)}
                  aria-expanded={!isCollapsed}
                >
                  {section.label}
                  <ChevronDown size={14} />
                </button>
                {!isCollapsed &&
                  section.items.map((item) => {
                    const Icon = item.icon;
                    return (
                      <NavLink
                        key={item.path}
                        to={item.path}
                        end={item.path === "/admin"}
                        className={({ isActive }) =>
                          isActive ? "selected" : ""
                        }
                        onClick={() => setMenuOpen(false)}
                      >
                        <Icon size={16} />
                        {item.label}
                      </NavLink>
                    );
                  })}
              </div>
            );
          })}
        </nav>
        <button
          type="button"
          className="admin-logout"
          onClick={handleLogout}
        >
          <LogOut size={16} />
          Logout
        </button>
      </aside>
      {menuOpen && (
        <div
          className="nav-backdrop"
          onClick={() => setMenuOpen(false)}
          aria-hidden="true"
        />
      )}
      <main className="admin-main">
        <div className="admin-topbar">
          <button
            type="button"
            className="nav-toggle"
            onClick={() => setMenuOpen((open) => !open)}
            aria-label="Toggle navigation"
            aria-expanded={menuOpen}
          >
            {menuOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
          <div className="admin-topbar-brand">
            <Bot size={17} />
            <span>AI Agent</span>
          </div>
          {user && <span className="admin-topbar-user">{user.email}</span>}
          <ThemeToggle variant="boxed" />
          <button
            type="button"
            className="login-link"
            onClick={() => navigate("/chat")}
          >
            Open chat
          </button>
        </div>
        <Outlet />
      </main>
    </div>
  );
}
