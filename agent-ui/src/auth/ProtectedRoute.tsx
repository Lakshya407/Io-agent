/**
 * Authentication route guard.
 *
 * Wraps every route that requires a signed-in user (`/chat`, `/admin/*`).
 * While the session is still being validated only `AuthLoading` renders, so
 * the Chat/Admin UI never appears before authentication is resolved.
 *
 * Unauthenticated visitors are sent to `/login` with the destination they
 * tried to reach preserved in the `redirect` query parameter.
 *
 * This is a UX/navigation layer only — the FastAPI backend remains the actual
 * security authority on every request.
 */
import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import AuthLoading from "./AuthLoading";

export default function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <AuthLoading />;
  }

  if (!isAuthenticated) {
    return (
      <Navigate
        to={`/login?redirect=${encodeURIComponent(location.pathname)}`}
        replace
      />
    );
  }

  return <Outlet />;
}
