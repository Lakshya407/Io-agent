/**
 * Minimal session-loading screen.
 *
 * Shown while `AuthContext` restores/validates the session with the backend so
 * that no protected UI (Chat or Admin) can flash before authentication is
 * resolved. See the route guards in this folder — they render this instead of
 * their children whenever `isLoading` is true.
 */
import { Bot } from "lucide-react";

export default function AuthLoading() {
  return (
    <div className="admin-login" data-testid="auth-loading">
      <div className="login-card auth-loading">
        <Bot size={24} />
        <strong>AI Agent</strong>
        <small>Checking authentication…</small>
      </div>
    </div>
  );
}
