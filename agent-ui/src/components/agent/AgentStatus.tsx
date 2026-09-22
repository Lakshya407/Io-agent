import { CheckCircle2, CircleDot, LoaderCircle, XCircle } from "lucide-react";

export type AgentState = "online" | "working" | "completed" | "error";

export default function AgentStatus({
  state = "online",
}: {
  state?: AgentState;
}) {
  const content =
    state === "working"
      ? {
          icon: <LoaderCircle size={13} className="spin" />,
          label: "Processing",
          className: "working",
        }
      : state === "completed"
        ? {
            icon: <CheckCircle2 size={13} />,
            label: "Completed",
            className: "completed",
          }
        : state === "error"
          ? {
              icon: <XCircle size={13} />,
              label: "Error",
              className: "error",
            }
          : {
              icon: <CircleDot size={13} />,
              label: "Online",
              className: "online",
            };
  return (
    <span className={`agent-status ${content.className}`}>
      {content.icon}
      {content.label}
    </span>
  );
}
