export interface BarChartData {
  label: string;
  value: number;
  display: string;
}

interface BarChartProps {
  data: BarChartData[];
}

export default function BarChart({ data }: BarChartProps) {
  const max = Math.max(...data.map((item) => item.value), 1);
  return (
    <div className="bar-chart">
      {data.map((item) => (
        <div className="bar-col" key={item.label}>
          <span className="bar-value">{item.display}</span>
          <div className="bar-track">
            <div
              className="bar"
              style={{ height: `${Math.round((item.value / max) * 100)}%` }}
              title={`${item.display} on ${item.label}`}
            />
          </div>
          <span className="bar-label">{item.label}</span>
        </div>
      ))}
    </div>
  );
}
