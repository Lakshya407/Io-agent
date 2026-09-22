import { CheckCircle2, LoaderCircle, XCircle, Zap } from "lucide-react";
import type { ToolCallEntry } from "./ActivityPanel";

function formatDuration(ms?: number): string | null {
  if (ms === undefined || ms === null) return null;
  if (ms < 1000) return `${Math.max(1, Math.round(ms))}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

/**
 * One entry in the agent activity panel. `entry` is passed whole so the panel
 * stays in sync with the live request lifecycle (running → completed/failed).
 */
export default function ToolCall({ entry }: { entry: ToolCallEntry }) {
  const duration = formatDuration(entry.durationMs);
  return (
    <div className="tool-call">
      <div className="tool-title">
        <Zap size={13} />
        <span>{entry.name}</span>
        {entry.status === "running" ? (
          <span className="tool-running">Running</span>
        ) : (
          <>
            {duration && <span className="tool-duration">{duration}</span>}
            {entry.status === "failed" ? (
              <XCircle size={13} className="error" />
            ) : (
              <CheckCircle2 size={13} className="success" />
            )}
          </>
        )}
      </div>
      {entry.detail && <p>{entry.detail}</p>}
    </div>
  );
}
