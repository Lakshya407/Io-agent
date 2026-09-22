interface ProgressBarProps {
  percent: number;
  variant?: "default" | "mini";
  label?: string;
}

export default function ProgressBar({
  percent,
  variant = "default",
  label,
}: ProgressBarProps) {
  const clamped = Math.min(100, Math.max(0, percent));
  return (
    <div
      className={`progress${variant === "mini" ? " mini" : ""}`}
      role="progressbar"
      aria-label={label ?? "progress"}
      aria-valuenow={clamped}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div className="progress-fill" style={{ width: `${clamped}%` }} />
    </div>
  );
}
