import { Navigate, Route, Routes } from "react-router-dom";
import AdminActivity from "./pages/admin/AdminActivity";
import AdminAnalytics from "./pages/admin/AdminAnalytics";
import AdminApiUsage from "./pages/admin/AdminApiUsage";
import AdminAuditLogs from "./pages/admin/AdminAuditLogs";
import AdminKnowledgeBase from "./pages/admin/AdminKnowledgeBase";
import AdminLayout from "./pages/admin/AdminLayout";
import AdminModels from "./pages/admin/AdminModels";
import AdminOverview from "./pages/admin/AdminOverview";
import AdminPrompts from "./pages/admin/AdminPrompts";
import AdminRateLimits from "./pages/admin/AdminRateLimits";
import AdminRouting from "./pages/admin/AdminRouting";
import AdminTools from "./pages/admin/AdminTools";
import AdminUsage from "./pages/admin/AdminUsage";
import AdminUsers from "./pages/admin/AdminUsers";
import Chat from "./pages/Chat";
import ForbiddenRedirect from "./auth/ForbiddenRedirect";
import Login from "./pages/Login";
import ProtectedRoute from "./auth/ProtectedRoute";
import Register from "./pages/Register";
import RoleRoute from "./auth/RoleRoute";
import RootRedirect from "./auth/RootRedirect";
import Unauthorized from "./pages/Unauthorized";

/**
 * Authentication-first routing.
 *
 * ```text
 * /                     → RootRedirect (loading → /login → /admin | /chat)
 * /login, /register     → public
 * /unauthorized         → authenticated but not permitted (403)
 *
 * ProtectedRoute        → requires a valid session (any signed-in user)
 *    /chat
 *    RoleRoute(admin)   → additionally requires the real backend role
 *       /admin/*
 * ```
 *
 * The guards only control navigation and rendering. Every request is
 * authorized by FastAPI, so changing role data in the browser cannot grant
 * access: admin endpoints return `403` to normal users regardless of what
 * the frontend believes.
 */
export default function App() {
  return (
    <>
      {/* Listens for API 401/403 outcomes and keeps the UI in sync. */}
      <ForbiddenRedirect />
      <Routes>
        {/* Public */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/unauthorized" element={<Unauthorized />} />

        {/*
         * There is one authentication flow. The old separate admin sign-in is
         * gone; anyone hitting it is pointed at the single login page, which
         * routes by role after authenticating.
         */}
        <Route path="/admin/login" element={<Navigate to="/login" replace />} />

        {/* Authenticated application entry point (never renders Chat directly) */}
        <Route path="/" element={<RootRedirect />} />

        {/* Everything below requires a valid session */}
        <Route element={<ProtectedRoute />}>
          <Route path="/chat" element={<Chat />} />

          {/* Admin area: session + admin role from GET /auth/me */}
          <Route element={<RoleRoute requiredRole="admin" />}>
            <Route path="/admin" element={<AdminLayout />}>
              <Route index element={<AdminOverview />} />
              <Route path="users" element={<AdminUsers />} />
              <Route path="analytics" element={<AdminAnalytics />} />
              <Route path="usage" element={<AdminUsage />} />
              <Route path="api-usage" element={<AdminApiUsage />} />
              <Route path="models" element={<AdminModels />} />
              <Route path="routing" element={<AdminRouting />} />
              <Route path="knowledge-base" element={<AdminKnowledgeBase />} />
              <Route path="tools" element={<AdminTools />} />
              <Route path="prompts" element={<AdminPrompts />} />
              <Route path="activity" element={<AdminActivity />} />
              <Route path="audit-logs" element={<AdminAuditLogs />} />
              <Route path="rate-limits" element={<AdminRateLimits />} />
            </Route>
          </Route>
        </Route>

        {/* Unknown paths resolve through the role-aware root redirect */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}
