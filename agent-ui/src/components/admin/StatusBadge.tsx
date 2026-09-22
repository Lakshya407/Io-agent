interface StatusBadgeProps {
  status: string;
}

const green = ["active", "ready", "operational", "completed", "success"];
const red = [
  "inactive",
  "disabled",
  "failed",
  "down",
  "error",
  "blocked",
];
const amber = [
  "processing",
  "in progress",
  "draft",
  "invited",
  "pending",
  "queued",
];

function variantClass(status: string): string {
  const normalized = status.toLowerCase();
  if (green.includes(normalized)) return "pill active";
  if (red.includes(normalized)) return "pill inactive";
  if (amber.includes(normalized)) return "pill processing";
  return "pill";
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span className={variantClass(status)}>
      {status}
    </span>
  );
}
