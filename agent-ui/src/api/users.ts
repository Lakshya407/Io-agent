/**
 * Users API — `GET /users`, `GET /users/{id}`, `PATCH /users/{id}`,
 * `DELETE /users/{id}` (all admin-only).
 */

import { apiFetch } from "./client";
import type { PaginatedResponse, PageParams } from "../types/common";
import type { User } from "../types/auth";
import type { UserAdminUpdate, UserMeUpdate } from "../types/user";

export const usersApi = {
  /** `GET /api/v1/users` — list users (admin). */
  list(params: PageParams = {}): Promise<PaginatedResponse<User>> {
    return apiFetch<PaginatedResponse<User>>("/users", { params });
  },

  /** `GET /api/v1/users/{id}` (admin). */
  get(userId: string): Promise<User> {
    return apiFetch<User>(`/users/${userId}`);
  },

  /** `PATCH /api/v1/users/{id}` (admin). */
  update(userId: string, payload: UserAdminUpdate): Promise<User> {
    return apiFetch<User>(`/users/${userId}`, { method: "PATCH", body: payload });
  },

  /** `DELETE /api/v1/users/{id}` (admin) — returns 204. */
  remove(userId: string): Promise<void> {
    return apiFetch<void>(`/users/${userId}`, { method: "DELETE" });
  },

  /** `PUT /api/v1/users/me`. */
  updateMe(payload: UserMeUpdate): Promise<User> {
    return apiFetch<User>("/users/me", { method: "PUT", body: payload });
  },
};
