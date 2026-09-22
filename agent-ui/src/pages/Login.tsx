/**
 * User login page (`/login`).
 *
 * Authenticates a normal chat user against the FastAPI backend. The visual
 * design reuses the application's existing authentication styling so it stays
 * consistent with the admin sign-in; no new design system is introduced.
 *
 * Flow: form validation -> POST /auth/login -> tokens -> GET /auth/me ->
 * role-based redirect (admin -> /admin, user -> /chat, or the originally
 * requested page when this role may reach it).
 */
import { Bot, Eye, EyeOff, LoaderCircle, Lock, User } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { resolveRedirect } from "../auth/routing";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import ThemeToggle from "../components/ui/ThemeToggle";
import { APIError } from "../types/common";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const { login } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // Where the user originally tried to go (captured by ProtectedRoute), or
  // nothing when they opened the login page directly. `resolveRedirect` picks
  // the role default and never routes a normal user into /admin.
  const requested = searchParams.get("redirect");

  const validate = (): boolean => {
    const next: Record<string, string> = {};
    if (!email.trim()) next.email = "Email is required.";
    else if (!EMAIL_RE.test(email.trim()))
      next.email = "Enter a valid email address.";
    if (!password) next.password = "Password is required.";
    setFieldErrors(next);
    return Object.keys(next).length === 0;
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (submitting) return; // prevent duplicate login requests
    setError("");
    if (!validate()) return;

    setSubmitting(true);
    try {
      const loggedIn = await login(email.trim(), password, remember);
      toast("Signed in successfully.", "success");
      // Route by the real backend role: admin → /admin, user → /chat. The
      // requested destination is honoured only when this role may reach it.
      navigate(resolveRedirect(requested, loggedIn), { replace: true });
    } catch (err) {
      const message =
        err instanceof APIError && err.isUnauthorized
          ? "Invalid email or password."
          : err instanceof APIError
            ? err.message
            : "Unable to connect to the server. Please try again.";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="admin-login">
      <div className="auth-theme-toggle">
        <ThemeToggle variant="boxed" />
      </div>
      <form className="login-card" onSubmit={submit} noValidate>
        <div className="login-brand">
          <span className="login-mark" aria-hidden="true">
            <Bot size={24} />
          </span>
          <strong>AI Agent</strong>
          <small>Sign in to your intelligent workspace assistant</small>
        </div>

        <label className="field">
          <span>Email</span>
          <div className="field-input">
            <User size={15} />
            <input
              type="email"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                if (fieldErrors.email)
                  setFieldErrors((current) => ({ ...current, email: "" }));
              }}
              placeholder="you@example.com"
              autoComplete="email"
              disabled={submitting}
              aria-invalid={!!fieldErrors.email}
            />
          </div>
          {fieldErrors.email && (
            <span className="login-error">{fieldErrors.email}</span>
          )}
        </label>

        <label className="field">
          <span>Password</span>
          <div className="field-input">
            <Lock size={15} />
            <input
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                if (fieldErrors.password)
                  setFieldErrors((current) => ({ ...current, password: "" }));
              }}
              placeholder="••••••••"
              autoComplete="current-password"
              disabled={submitting}
              aria-invalid={!!fieldErrors.password}
            />
            <button
              type="button"
              className="eye-toggle"
              onClick={() => setShowPassword((current) => !current)}
              aria-label={showPassword ? "Hide password" : "Show password"}
              title={showPassword ? "Hide password" : "Show password"}
              tabIndex={-1}
            >
              {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
            </button>
          </div>
          {fieldErrors.password && (
            <span className="login-error">{fieldErrors.password}</span>
          )}
        </label>

        <div className="remember-row">
          <label className="remember">
            <input
              type="checkbox"
              checked={remember}
              onChange={(e) => setRemember(e.target.checked)}
              disabled={submitting}
            />
            <span>Remember me</span>
          </label>
          <button
            type="button"
            className="login-link"
            title="Password reset is not available yet"
            onClick={() =>
              toast(
                "Password reset isn't available yet. Contact an administrator.",
                "info",
              )
            }
          >
            Forgot password?
          </button>
        </div>

        {error && <p className="login-error" role="alert">{error}</p>}

        <button
          className="login-btn"
          type="submit"
          disabled={submitting}
          aria-busy={submitting}
        >
          {submitting ? (
            <>
              <LoaderCircle size={16} className="spin" /> Signing in…
            </>
          ) : (
            "Sign in"
          )}
        </button>

        <p className="auth-footnote">
          Don&rsquo;t have an account?{" "}
          <Link to="/register" className="auth-link">
            Create account
          </Link>
        </p>
      </form>
    </div>
  );
}
