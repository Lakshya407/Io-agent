/**
 * User menu for the chat sidebar footer.
 *
 * Replaces the static branding block with the authenticated user and a
 * dropdown offering sign-out (plus an admin-console shortcut for admins).
 * Logout clears all client-side credentials and query cache; there is no
 * server-side logout endpoint, so nothing is falsified.
 */
import { ChevronUp, LogOut, Shield } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { useToast } from "../../context/ToastContext";

export default function UserMenu({ variant = "full" }: { variant?: "full" | "compact" }) {
  const { user, logout, isAdmin } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Close the dropdown when clicking outside of it.
  useEffect(() => {
    if (!open) return;
    const onDocumentClick = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onDocumentClick);
    return () => document.removeEventListener("mousedown", onDocumentClick);
  }, [open]);

  if (!user) return null;

  const initials = (user.name || user.email)
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join("");

  const signOut = () => {
    logout();
    toast("You have been signed out.", "info");
    // No explicit navigation: clearing the session makes ProtectedRoute
    // redirect to /login (preserving the page the user was on).
  };

  return (
    <div className={`user-menu ${variant === "compact" ? "user-menu-compact" : ""}`} ref={ref}>
      <button
        type="button"
        className="user-menu-trigger"
        onClick={() => setOpen((current) => !current)}
        aria-expanded={open}
        aria-haspopup="menu"
      >
        <span className="user-avatar" aria-hidden="true">
          {initials || "?"}
        </span>
        {variant === "full" && (
          <>
            <span className="user-menu-meta">
              <strong>{user.name}</strong>
              <small>{user.email}</small>
            </span>
            <ChevronUp size={14} className="user-menu-chev" />
          </>
        )}
      </button>

      {open && (
        <div className="user-menu-popover" role="menu">
          <div className="user-menu-header">
            <span className="user-avatar" aria-hidden="true">
              {initials || "?"}
            </span>
            <div>
              <strong>{user.name}</strong>
              <small>{user.email}</small>
            </div>
          </div>
          {isAdmin && (
            <button
              type="button"
              className="user-menu-item"
              role="menuitem"
              onClick={() => {
                setOpen(false);
                navigate("/admin");
              }}
            >
              <Shield size={14} />
              Admin console
            </button>
          )}
          <button
            type="button"
            className="user-menu-item danger"
            role="menuitem"
            onClick={signOut}
          >
            <LogOut size={14} />
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}
