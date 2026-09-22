/**
 * Loading + error states for API-driven sections.
 *
 * Reuses the existing visual language (`.spin`, `.btn-secondary`,
 * `.table-empty`) so no restyling of the application is required.
 */

import { LoaderCircle } from "lucide-react";
import { describeStatus, APIError } from "../../types/common";

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="state-inline">
      <LoaderCircle size={16} className="spin" />
      <span>{label}</span>
    </div>
  );
}

interface ErrorStateProps {
  error: unknown;
  onRetry?: () => void;
  /** Label shown before the generic message, e.g. "Unable to load users." */
  context?: string;
}

export function ErrorState({ error, onRetry, context }: ErrorStateProps) {
  const isApiError = error instanceof APIError;
  const headline = context ?? "Something went wrong.";
  // Never surface raw backend stack traces; the backend envelope already
  // carries a safe `message`.
  const detail = isApiError ? error.message : describeStatus(0);
  return (
    <div className="state-error">
      <strong>{headline}</strong>
      <span>{detail}</span>
      {onRetry && (
        <button
          type="button"
          className="btn btn-sm btn-secondary"
          onClick={onRetry}
        >
          Try again
        </button>
      )}
    </div>
  );
}
