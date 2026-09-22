/**
 * Auth context — the single source of authentication truth for the UI.
 *
 * Exposes `user`, `isAuthenticated`, `isLoading`, `isAdmin`, `login()`,
 * `logout()` and `refreshUser()`. Components never inspect tokens directly;
 * role is derived from the authenticated backend user only (never hard-coded).
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { authApi } from "../api/auth";
import { tokenStore } from "../api/client";
import { queryClient } from "../lib/queryClient";
import type { User } from "../types/auth";

interface AuthContextValue {
  user: User | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  isLoading: boolean;
  login: (email: string, password: string, remember?: boolean) => Promise<User>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  // `isLoading` covers the initial session-restore check only.
  const [isLoading, setIsLoading] = useState(true);

  const loadUser = useCallback(async (): Promise<User | null> => {
    if (!tokenStore.getAccessToken() && !tokenStore.getRefreshToken()) {
      return null;
    }
    try {
      return await authApi.me();
    } catch {
      // The API client already attempts a single token refresh on 401; if
      // `/auth/me` still fails there is no valid session.
      return null;
    }
  }, []);

  // Restore the session on first mount (silent refresh handled by the client).
  useEffect(() => {
    let active = true;
    loadUser().then((restored) => {
      if (!active) return;
      setUser(restored);
      setIsLoading(false);
    });
    return () => {
      active = false;
    };
  }, [loadUser]);

  // React to forced logouts issued by the API client (refresh failure).
  useEffect(() => tokenStore.onForcedLogout(() => setUser(null)), []);

  const login = useCallback(
    async (email: string, password: string, remember = true): Promise<User> => {
      const tokens = await authApi.login(email, password);
      tokenStore.setTokens(
        tokens.access_token,
        tokens.refresh_token,
        remember,
      );
      const loggedIn = await authApi.me();
      setUser(loggedIn);
      // Return the freshly authenticated user so callers can route by the
      // real backend role without reading stale context state.
      return loggedIn;
    },
    [],
  );

  const logout = useCallback(() => {
    authApi.logout();
    setUser(null);
    queryClient.clear();
  }, []);

  const refreshUser = useCallback(async (): Promise<void> => {
    const fresh = await loadUser();
    setUser(fresh);
  }, [loadUser]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: user !== null,
      isAdmin: user?.role === "admin",
      isLoading,
      login,
      logout,
      refreshUser,
    }),
    [user, isLoading, login, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
