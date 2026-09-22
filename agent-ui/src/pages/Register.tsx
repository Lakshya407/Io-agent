/**
 * Register page (`/register`).
 *
 * Creates a real backend account via `POST /api/v1/auth/register`, then
 * authenticates the user immediately (the backend issues tokens on success).
 * No frontend-only accounts are created.
 */
import { Bot, LoaderCircle, Lock, Mail, User } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { authApi } from "../api/auth";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import ThemeToggle from "../components/ui/ThemeToggle";
import { APIError } from "../types/common";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MIN_PASSWORD = 6;

export default function Register() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const { login } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();

  const validate = (): boolean => {
    const next: Record<string, string> = {};
    if (!name.trim()) next.name = "Name is required.";
    if (!email.trim()) next.email = "Email is required.";
    else if (!EMAIL_RE.test(email.trim()))
      next.email = "Enter a valid email address.";
    if (!password) next.password = "Password is required.";
    else if (password.length < MIN_PASSWORD)
      next.password = `Use at least ${MIN_PASSWORD} characters.`;
    if (confirm !== password) next.confirm = "Passwords do not match.";
    setFieldErrors(next);
    return Object.keys(next).length === 0;
  };

  const clear = (key: string) =>
    fieldErrors[key] &&
    setFieldErrors((current) => ({ ...current, [key]: "" }));

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (submitting) return;
    setError("");
    if (!validate()) return;

    setSubmitting(true);
    try {
      await authApi.register({
        name: name.trim(),
        email: email.trim(),
        password,
      });
      // The backend creates the account; sign the user straight in.
      await login(email.trim(), password, true);
      toast("Account created. Welcome!", "success");
      navigate("/chat", { replace: true });
    } catch (err) {
      const message =
        err instanceof APIError && err.status === 409
          ? "An account with this email already exists."
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
          <small>Create your account</small>
        </div>

        <label className="field">
          <span>Name</span>
          <div className="field-input">
            <User size={15} />
            <input
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                clear("name");
              }}
              placeholder="Your name"
              autoComplete="name"
              disabled={submitting}
              aria-invalid={!!fieldErrors.name}
            />
          </div>
          {fieldErrors.name && (
            <span className="login-error">{fieldErrors.name}</span>
          )}
        </label>

        <label className="field">
          <span>Email</span>
          <div className="field-input">
            <Mail size={15} />
            <input
              type="email"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                clear("email");
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
              type="password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                clear("password");
              }}
              placeholder="••••••••"
              autoComplete="new-password"
              disabled={submitting}
              aria-invalid={!!fieldErrors.password}
            />
          </div>
          {fieldErrors.password && (
            <span className="login-error">{fieldErrors.password}</span>
          )}
        </label>

        <label className="field">
          <span>Confirm password</span>
          <div className="field-input">
            <Lock size={15} />
            <input
              type="password"
              value={confirm}
              onChange={(e) => {
                setConfirm(e.target.value);
                clear("confirm");
              }}
              placeholder="••••••••"
              autoComplete="new-password"
              disabled={submitting}
              aria-invalid={!!fieldErrors.confirm}
            />
          </div>
          {fieldErrors.confirm && (
            <span className="login-error">{fieldErrors.confirm}</span>
          )}
        </label>

        {error && <p className="login-error" role="alert">{error}</p>}

        <button
          className="login-btn"
          type="submit"
          disabled={submitting}
          aria-busy={submitting}
        >
          {submitting ? (
            <>
              <LoaderCircle size={16} className="spin" /> Creating account…
            </>
          ) : (
            "Create account"
          )}
        </button>

        <p className="auth-footnote">
          Already have an account?{" "}
          <Link to="/login" className="auth-link">
            Sign in
          </Link>
        </p>
      </form>
    </div>
  );
}
