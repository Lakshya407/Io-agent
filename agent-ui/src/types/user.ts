/**
 * User-management types — mirror `app/schemas/user.py`.
 */

import type { UserRole } from "./auth";

/** `UserAdminUpdate` — payload for PATCH /api/v1/users/{id} (admin only). */
export interface UserAdminUpdate {
  name?: string | null;
  email?: string | null;
  role?: UserRole | null;
  is_active?: boolean | null;
}

/** `UserMeUpdate` — payload for PUT /api/v1/users/me. */
export interface UserMeUpdate {
  name?: string | null;
  email?: string | null;
}
