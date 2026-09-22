/**
 * Unauthorized page (`/unauthorized`).
 *
 * Reached when an authenticated user tries a route or resource their role
 * does not allow (backend returned `403 Forbidden`). The session is intact,
 * so the user is offered a way back to their own area rather than a login
 * prompt.
 */
import { ArrowLeft, ShieldX } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { defaultRouteFor } from "../auth/routing";

export default function Unauthorized() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const back = user ? defaultRouteFor(user) : "/login";

  return (
    <div className="admin-login">
      <div className="login-card auth-loading">
        <ShieldX size={26} />
        <strong>Access denied</strong>
        <small>
          You do not have permission to access this page. Your account does not
          have the required role.
        </small>
        <button
          type="button"
          className="login-btn"
          onClick={() => navigate(back, { replace: true })}
        >
          <ArrowLeft size={15} />
          Back to your workspace
        </button>
      </div>
    </div>
  );
}
