/**
 * Smart root entry point (`/`).
 *
 * The root never renders the Chat UI directly. It resolves the session first
 * and then redirects by role:
 *
 *     loading           → AuthLoading (no app UI flashes)
 *     unauthenticated   → /login
 *     role = admin      → /admin
 *     role = user       → /chat
 */
import { Navigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { defaultRouteFor } from "./routing";
import AuthLoading from "./AuthLoading";

export default function RootRedirect() {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return <AuthLoading />;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <Navigate to={defaultRouteFor(user)} replace />;
}
