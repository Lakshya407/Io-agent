/**
 * Auth API — `POST /auth/login`, `POST /auth/refresh`, `GET /auth/me`.
 */

import { apiFetch, tokenStore } from "./client";
import type {
  RefreshRequest,
  RegisterRequest,
  TokenResponse,
  User,
} from "../types/auth";

export const authApi = {
  /** `POST /api/v1/auth/login` — OAuth2 form (username = email). */
  login(email: string, password: string): Promise<TokenResponse> {
    return apiFetch<TokenResponse>("/auth/login", {
      method: "POST",
      asForm: true,
      skipAuth: true,
      body: { username: email, password, grant_type: "password" },
    });
  },

  /** `POST /api/v1/auth/register`. */
  register(payload: RegisterRequest): Promise<TokenResponse> {
    return apiFetch<TokenResponse>("/auth/register", {
      method: "POST",
      skipAuth: true,
      body: payload,
    });
  },

  /** `POST /api/v1/auth/refresh`. */
  refresh(payload: RefreshRequest): Promise<TokenResponse> {
    return apiFetch<TokenResponse>("/auth/refresh", {
      method: "POST",
      skipAuth: true,
      body: payload,
    });
  },

  /** `GET /api/v1/auth/me` — the currently authenticated user. */
  me(): Promise<User> {
    return apiFetch<User>("/auth/me");
  },

  /** Drop all stored credentials (client-side half of logout). */
  logout(): void {
    tokenStore.clear();
  },
};
