/**
 * Shared API primitives — mirror the backend's common response shapes.
 */

/** Backend paginated envelope: `{ items, page, page_size, total }`. */
export interface PaginatedResponse<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
}

/** Query parameters accepted by every paginated backend endpoint. */
export interface PageParams {
  page?: number;
  page_size?: number;
}

/**
 * Normalised error raised by the API client for every failed request.
 *
 * The backend uses a consistent envelope:
 * `{ success: false, error: { code, message }, request_id }`
 * Standard FastAPI auth errors use `{ detail }` — both are handled.
 */
export class APIError extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId?: string;
  readonly details?: unknown;

  constructor(params: {
    status: number;
    code: string;
    message: string;
    requestId?: string;
    details?: unknown;
  }) {
    super(params.message);
    this.name = "APIError";
    this.status = params.status;
    this.code = params.code;
    this.requestId = params.requestId;
    this.details = params.details;
  }

  /** True for network failures, timeouts and 5xx responses. */
  get isTransient(): boolean {
    return this.status === 0 || this.status >= 500;
  }

  /** True for authentication failures (expired/invalid/missing token). */
  get isUnauthorized(): boolean {
    return this.status === 401;
  }

  /** True for authorization failures (authenticated but not permitted). */
  get isForbidden(): boolean {
    return this.status === 403;
  }
}

/** User-facing message for a status code, never exposing stack traces. */
export function describeStatus(status: number): string {
  switch (status) {
    case 0:
      return "Unable to reach the server. Check your connection and try again.";
    case 400:
      return "The request was invalid. Please review the details and try again.";
    case 401:
      return "Your session has expired. Please sign in again.";
    case 403:
      return "You do not have permission to perform this action.";
    case 404:
      return "The requested resource could not be found.";
    case 409:
      return "This resource already exists.";
    case 422:
      return "Some details were invalid. Please review the form and try again.";
    case 429:
      return "Too many requests. Please wait a moment and try again.";
    case 500:
    case 502:
    case 503:
    case 504:
      return "Something went wrong on the server. Please try again.";
    default:
      return "An unexpected error occurred. Please try again.";
  }
}
