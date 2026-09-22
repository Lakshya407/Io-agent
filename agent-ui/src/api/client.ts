/**
 * Centralized API client.
 *
 * Every backend request goes through `apiFetch`. It handles:
 *   - base URL resolution from `VITE_API_BASE_URL`
 *   - JSON + auth headers (injected, never repeated per component)
 *   - request id propagation (`X-Request-ID`)
 *   - timeouts via AbortController
 *   - normalisation of the backend error envelope into `APIError`
 *   - single-flight access-token refresh + transparent retry on 401
 *   - 403 stays a 403 (session kept) and is surfaced to the UI
 *   - one bounded retry for idempotent GET requests on transient failures
 *
 * Components and hooks should never call `fetch` directly.
 */

import { APIError, describeStatus } from "../types/common";

const BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

/** Default request timeout (ms). Chat uses a longer timeout (see api/chat.ts). */
const DEFAULT_TIMEOUT = 20_000;
/** One retry for GET requests on transient (network/5xx) failures. */
const GET_MAX_RETRIES = 1;

const ACCESS_TOKEN_KEY = "ai-agent.access_token";
const REFRESH_TOKEN_KEY = "ai-agent.refresh_token";

type listener = () => void;
const authListeners = new Set<listener>();
// Separate listeners for authorization failures (403). A 403 is deliberately
// NOT treated like a 401: the user is authenticated but not permitted, so the
// session stays intact and only the UI reacts (see ForbiddenRedirect).
const forbiddenListeners = new Set<listener>();

function readStorage(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeStorage(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* storage unavailable (private mode) — keep tokens in memory only */
  }
}

function dropStorage(key: string): void {
  try {
    localStorage.removeItem(key);
  } catch {
    /* ignore */
  }
}

/**
 * Token storage.
 *
 * The short-lived access token is kept in memory only; the longer-lived
 * refresh token is persisted so a page refresh can silently restore the
 * session. This is the safest practical browser-side approach for the
 * backend's JWT (bearer-token) architecture, which does not use
 * HTTP-only cookies.
 */
let accessToken: string | null = readStorage(ACCESS_TOKEN_KEY);
let refreshToken: string | null = readStorage(REFRESH_TOKEN_KEY);

export const tokenStore = {
  getAccessToken(): string | null {
    return accessToken;
  },
  getRefreshToken(): string | null {
    return refreshToken;
  },
  setTokens(access: string, refresh: string, persist = true): void {
    accessToken = access;
    refreshToken = refresh;
    // "Remember me" controls whether the refresh token survives a browser
    // restart. When unchecked the session ends on reload — a real frontend
    // behaviour, not an invented server-side session extension.
    writeStorage(ACCESS_TOKEN_KEY, access);
    if (persist) {
      writeStorage(REFRESH_TOKEN_KEY, refresh);
    } else {
      dropStorage(REFRESH_TOKEN_KEY);
    }
  },
  clear(): void {
    accessToken = null;
    refreshToken = null;
    dropStorage(ACCESS_TOKEN_KEY);
    dropStorage(REFRESH_TOKEN_KEY);
    authListeners.forEach((listener) => listener());
  },
  /** Subscribe to forced-logout events (used by AuthContext). */
  onForcedLogout(listener: listener): () => void {
    authListeners.add(listener);
    return () => authListeners.delete(listener);
  },
  /** Subscribe to authorization-failure (403) events (used by the UI). */
  onForbidden(listener: listener): () => void {
    forbiddenListeners.add(listener);
    return () => forbiddenListeners.delete(listener);
  },
};

export interface ApiFetchOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  /** Query params, appended to the URL. */
  params?: object;
  /** Override the default timeout (ms). */
  timeoutMs?: number;
  /** Send as an OAuth2 form instead of JSON (login endpoint). */
  asForm?: boolean;
  /** Skip auth header + retry/refresh handling (login, register, refresh). */
  skipAuth?: boolean;
  /**
   * Treat `path` as already absolute from the server origin, bypassing the
   * `/api/v1` prefix (used by the unversioned `/health` probes).
   */
  absolute?: boolean;
}

function buildUrl(
  path: string,
  params?: object,
  absolute?: boolean,
): string {
  // Health probes live outside the `/api/v1` prefix; everything else joins it.
  const base = absolute
    ? BASE_URL.replace(/\/+$/, "").replace(/\/api\/v\d+$/, "")
    : BASE_URL.replace(/\/+$/, "");
  const target = path.startsWith("http")
    ? path
    : `${base.replace(/\/+$/, "")}/${path.replace(/^\/+/, "")}`;
  // A base URL is required when `target` is relative (production builds use a
  // same-origin path like `/api/v1`); it is ignored when `target` is absolute.
  const url = new URL(target, window.location.origin);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, String(value));
      }
    });
  }
  return url.toString();
}

function buildHeaders(options: ApiFetchOptions): Headers {
  const headers = new Headers();
  if (options.asForm) {
    headers.set("Content-Type", "application/x-www-form-urlencoded");
  } else {
    headers.set("Content-Type", "application/json");
    headers.set("Accept", "application/json");
  }
  if (!options.skipAuth) {
    const token = tokenStore.getAccessToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }
  // Propagate a request id so backend logs and client errors correlate.
  headers.set("X-Request-ID", crypto.randomUUID());
  return headers;
}

function serializeBody(options: ApiFetchOptions): BodyInit | undefined {
  if (options.body === undefined) return undefined;
  if (options.asForm) {
    const form = new URLSearchParams();
    Object.entries(options.body as Record<string, string>).forEach(
      ([key, value]) => form.set(key, String(value)),
    );
    return form.toString();
  }
  return JSON.stringify(options.body);
}

interface ErrorEnvelope {
  success?: boolean;
  error?: { code?: string; message?: string; details?: unknown };
  detail?: string;
  request_id?: string;
}

/** Convert a raw `fetch` failure / non-2xx response into `APIError`. */
async function toApiError(
  response: Response,
  requestId: string | null,
): Promise<APIError> {
  let envelope: ErrorEnvelope | null = null;
  try {
    envelope = (await response.json()) as ErrorEnvelope;
  } catch {
    envelope = null;
  }
  const code = envelope?.error?.code ?? "HTTP_ERROR";
  const message =
    envelope?.error?.message ??
    envelope?.detail ??
    describeStatus(response.status);
  return new APIError({
    status: response.status,
    code,
    message,
    requestId: envelope?.request_id ?? requestId ?? undefined,
    details: envelope?.error?.details,
  });
}

/** True when a GET request is safe to retry once (network failure / 5xx). */
function isRetryable(error: APIError): boolean {
  return error.isTransient;
}

let refreshPromise: Promise<string | null> | null = null;

/**
 * Exchange the refresh token for a new access token. Single-flighted so
 * concurrent 401s share one refresh request.
 */
async function refreshAccessToken(): Promise<string | null> {
  if (refreshPromise) return refreshPromise;
  const stored = tokenStore.getRefreshToken();
  if (!stored) return null;

  refreshPromise = (async () => {
    try {
      const response = await rawFetch("/auth/refresh", {
        method: "POST",
        body: { refresh_token: stored },
        skipAuth: true,
      });
      if (!response.ok) return null;
      const tokens = (await response.json()) as {
        access_token: string;
        refresh_token: string;
      };
      tokenStore.setTokens(tokens.access_token, tokens.refresh_token);
      return tokens.access_token;
    } catch {
      return null;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

/** Low-level fetch without auth/retry handling (used by the refresh flow). */
function rawFetch(path: string, options: ApiFetchOptions): Promise<Response> {
  const controller = new AbortController();
  const timeout = window.setTimeout(
    () => controller.abort(),
    options.timeoutMs ?? DEFAULT_TIMEOUT,
  );
  return fetch(buildUrl(path, options.params, options.absolute), {
    method: options.method ?? "GET",
    headers: buildHeaders(options),
    body: serializeBody(options),
    signal: controller.signal,
  }).finally(() => window.clearTimeout(timeout));
}

/**
 * Core request function used by every API module.
 *
 * @returns parsed JSON body (or `null` for 204 responses)
 * @throws  `APIError` for any non-2xx response, timeout or network failure
 */
export async function apiFetch<T>(
  path: string,
  options: ApiFetchOptions = {},
): Promise<T> {
  const method = options.method ?? "GET";
  const allowRetry = method === "GET";
  let attempt = 0;
  // A single token refresh is attempted per request, then we give up.
  let didRefresh = false;

  // eslint-disable-next-line no-constant-condition
  while (true) {
    const response = await rawFetch(path, options).catch((error: unknown) => {
      const aborted = error instanceof DOMException && error.name === "AbortError";
      throw new APIError({
        status: 0,
        code: aborted ? "TIMEOUT" : "NETWORK_ERROR",
        message: aborted
          ? "The request took too long. Please try again."
          : describeStatus(0),
      });
    });

    if (response.status === 204) return null as T;

    if (response.ok) {
      return (await response.json()) as T;
    }

    let error = await toApiError(response, response.headers.get("X-Request-ID"));

    // Transparently refresh an expired access token once, then retry once.
    if (error.isUnauthorized && !options.skipAuth && !didRefresh) {
      didRefresh = true;
      const refreshed = await refreshAccessToken();
      if (refreshed) {
        continue;
      }
      tokenStore.clear();
      throw error;
    }

    // Authorization failure (403): the user is authenticated but not allowed
    // to reach this resource. This is deliberately kept separate from 401 —
    // the session is NOT cleared and the error is not converted. The UI is
    // notified so it can show the unauthorized page; the error still bubbles
    // up so callers can render an inline message.
    if (error.isForbidden) {
      forbiddenListeners.forEach((listener) => listener());
      throw error;
    }

    // One bounded retry for idempotent GET requests on transient failures.
    if (allowRetry && isRetryable(error) && attempt < GET_MAX_RETRIES) {
      attempt += 1;
      continue;
    }

    throw error;
  }
}
