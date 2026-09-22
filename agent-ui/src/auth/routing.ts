/**
 * Post-authentication routing helpers.
 *
 * These decide *where to navigate* based on the authenticated user's real
 * backend role. They are navigation/UX helpers only — they never grant or
 * deny access. Route guards (`ProtectedRoute`, `RoleRoute`) and, ultimately,
 * the FastAPI backend enforce authorization.
 */
import type { User, UserRole } from "../types/auth";

/** Admins enter the admin console; everyone else enters chat. */
export function defaultRouteFor(user: User): string {
  return user.role === "admin" ? "/admin" : "/chat";
}

/**
 * True only for a same-origin app path (never `//host`, `http…`, or a bare
 * string), so a crafted `?redirect=` value can never leak the browser to
 * another origin.
 */
function isSafeInternalPath(path: string): boolean {
  return path.startsWith("/") && !path.startsWith("//") && !path.includes(":");
}

/**
 * Decide the destination after a successful login.
 *
 * The originally requested page (`redirect`, captured by `ProtectedRoute`) is
 * honoured when it is a safe internal path the user's role may reach — a
 * normal user is never pointed at an admin route even if they requested one.
 * Otherwise the role default is used.
 */
export function resolveRedirect(requested: string | null, user: User): string {
  if (requested && isSafeInternalPath(requested) && roleCanReach(user.role, requested)) {
    return requested;
  }
  return defaultRouteFor(user);
}

/**
 * Navigation-level reachability. Admins may reach anything; normal users are
 * kept out of `/admin/*`. Authoritative enforcement happens in `RoleRoute`
 * and on the backend (`get_current_admin` → `403`).
 */
export function roleCanReach(role: UserRole, path: string): boolean {
  if (role === "admin") return true;
  return !(path === "/admin" || path.startsWith("/admin/"));
}
