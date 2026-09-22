/**
 * Reacts to authorization failures raised anywhere in the API client.
 *
 * When a request comes back `403 Forbidden` the user is authenticated but not
 * allowed to reach that resource, so they are sent to the dedicated
 * unauthorized page. The session is left untouched (unlike a `401`, a valid
 * user can simply be unauthorized for a resource) and re-entry to
 * `/unauthorized` is guarded so no redirect loop can form.
 *
 * The current user is re-fetched from the backend first: the authoritative
 * role lives there, not in client state, so a role changed server-side is
 * reflected by the very next navigation.
 */
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

import { tokenStore } from "../api/client";
import { useAuth } from "../context/AuthContext";

const UNAUTHORIZED_PATH = "/unauthorized";

export default function ForbiddenRedirect() {
  const navigate = useNavigate();
  const { refreshUser } = useAuth();

  useEffect(() => {
    return tokenStore.onForbidden(() => {
      // Best-effort: never block the redirect on a failing refresh.
      void refreshUser().catch(() => {
        /* a 401 here is handled by the forced-logout path */
      });
      if (window.location.pathname !== UNAUTHORIZED_PATH) {
        navigate(UNAUTHORIZED_PATH, { replace: true });
      }
    });
  }, [navigate, refreshUser]);

  return null;
}
