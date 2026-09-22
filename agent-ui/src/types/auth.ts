/**
 * Auth types — mirror `app/schemas/auth.py` and `app/schemas/user.py`.
 */

export type UserRole = "admin" | "user";

/** `UserOut` — public user representation. */
export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

/** `TokenResponse` — JWT pair returned by login/register/refresh. */
export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

/** `RegisterRequest`. */
export interface RegisterRequest {
  email: string;
  password: string;
  name: string;
}

/** `RefreshRequest`. */
export interface RefreshRequest {
  refresh_token: string;
}
