/**
 * Role-based route guard.
 *
 * Sits inside a `ProtectedRoute` (so authentication is already established)
 * and additionally requires the authenticated user's real backend role —
 * fetched from `GET /auth/me`, never from local storage — to match
 * `requiredRole`. A mismatch means the user is signed in but not permitted,
 * which is a `403` scenario, so they are sent to `/unauthorized` rather than
 * to login (a valid user can simply be unauthorized for a resource).
 *
 * Navigation protection only. The backend independently enforces RBAC and
 * returns `403 Forbidden` for any admin endpoint called by a normal user.
 */
import { Navigate, Outlet } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import type { UserRole } from "../types/auth";
import AuthLoading from "./AuthLoading";

export default function RoleRoute({
  requiredRole = "admin",
}: {
  requiredRole?: UserRole;
}) {
  const { user, isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return <AuthLoading />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (user?.role !== requiredRole) {
    return <Navigate to="/unauthorized" replace />;
  }

  return <Outlet />;
}
