/**
 * Agent Activity panel.
 *
 * Reflects the real lifecycle of the last request for the open conversation:
 * idle → processing → completed/error, with the model call, its measured
 * duration and token usage. Nothing is fabricated: an idle session shows an
 * idle state. The shape supports additional tool calls if the backend wires
 * them up later.
 */
import { X } from "lucide-react";
import AgentStatus, { type AgentState } from "./AgentStatus";
import ToolCall from "./ToolCall";
import { formatTokens } from "../../utils/format";

export type ActivityStatus = "idle" | "processing" | "completed" | "stopped" | "error";

export interface ToolCallEntry {
  id: string;
  name: string;
  detail?: string;
  status: "running" | "completed" | "failed";
  durationMs?: number;
}

export interface ActivityState {
  status: ActivityStatus;
  startedAt?: number;
  endedAt?: number;
  model?: string;
  toolCalls: ToolCallEntry[];
  error?: string;
  usage?: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}

export const emptyActivity = (): ActivityState => ({
  status: "idle",
  toolCalls: [],
});

const PIPELINE = ["Understanding request", "Generating response"];

function elapsedMs(activity: ActivityState): number | undefined {
  if (activity.startedAt === undefined) return undefined;
  const end = activity.endedAt ?? performance.now();
  return end - activity.startedAt;
}

interface ActivityPanelProps {
  activity: ActivityState;
  onClose: () => void;
}

export default function ActivityPanel({
  activity,
  onClose,
}: ActivityPanelProps) {
  const { status, toolCalls, error, usage, model } = activity;
  const agentState: AgentState =
    status === "processing"
      ? "working"
      : status === "completed" || status === "stopped"
        ? "completed"
        : status === "error"
          ? "error"
          : "online";

  const elapsed = elapsedMs(activity);
  const failed = status === "error";
  const stopped = status === "stopped";

  return (
    <aside className="activity-panel" aria-label="Agent activity">
      <div className="panel-heading">
        <h2>Agent Activity</h2>
        <div className="panel-heading-right">
          <AgentStatus state={agentState} />
          <button
            type="button"
            className="panel-close"
            onClick={onClose}
            aria-label="Close activity panel"
            title="Close activity panel"
          >
            <X size={15} />
          </button>
        </div>
      </div>

      {status === "idle" ? (
        <p className="activity-idle">
          No activity yet. Send a message to watch the agent work.
        </p>
      ) : (
        <>
          <div className="section-label">Pipeline</div>
          <div className="activity-list">
            {PIPELINE.map((step, index) => {
              const isLast = index === PIPELINE.length - 1;
              const done =
                status === "completed" ||
                status === "stopped" ||
                (failed && !isLast);
              const running = status === "processing" && isLast;
              return (
                <div
                  className={`activity-step ${running ? "active" : ""} ${
                    failed && isLast ? "failed" : ""
                  }`}
                  key={step}
                >
                  <span aria-hidden="true">
                    {done ? "✓" : failed && isLast ? "×" : running ? "◌" : "·"}
                  </span>
                  {step}
                  {stopped && isLast ? " (stopped)" : ""}
                </div>
              );
            })}
          </div>

          {model && (
            <div className="activity-model">
              <span className="activity-model-name">{model}</span>
              {elapsed !== undefined && (
                <span className="activity-model-time">
                  {(elapsed / 1000).toFixed(1)}s
                </span>
              )}
            </div>
          )}

          <div className="section-label">Tool calls</div>
          <div className="tool-list">
            {toolCalls.length === 0 ? (
              <p className="activity-idle">No tool calls in this request.</p>
            ) : (
              toolCalls.map((entry) => (
                <ToolCall entry={entry} key={entry.id} />
              ))
            )}
          </div>

          {usage && usage.total_tokens > 0 && (
            <>
              <div className="section-label">Tokens</div>
              <div className="token-split">
                <div className="token-item">
                  <span className="token-label">Prompt</span>
                  <span className="token-value">
                    {formatTokens(usage.prompt_tokens)}
                  </span>
                </div>
                <div className="token-item">
                  <span className="token-label">Completion</span>
                  <span className="token-value">
                    {formatTokens(usage.completion_tokens)}
                  </span>
                </div>
                <div className="token-item">
                  <span className="token-label">Total</span>
                  <span className="token-value accent">
                    {formatTokens(usage.total_tokens)}
                  </span>
                </div>
              </div>
            </>
          )}

          {error && (
            <div className="activity-error" role="alert">
              <strong>Request failed</strong>
              <span>{error}</span>
            </div>
          )}
        </>
      )}
    </aside>
  );
}
