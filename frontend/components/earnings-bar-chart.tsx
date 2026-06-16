import { useState } from "react";

type BarChartProps = {
  labels: string[];
  values: number[];
  color?: string;
  height?: number;
};

function formatAmount(n: number) {
  return n >= 100
    ? `$${(n / 100).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    : `${n}¢`;
}

const VB_W = 300;
const VB_PAD = 8;

export function EarningsBarChart({
  labels,
  values,
  color = "#6366f1",
  height = 80,
}: BarChartProps) {
  const vbH = 60;
  const [activeIdx, setActiveIdx] = useState<number | null>(null);

  const max = Math.max(...values, 1);
  const n = values.length;

  const xStep = n > 1 ? (VB_W - VB_PAD * 2) / (n - 1) : 0;
  const pts = values.map((v, i) => ({
    x: n > 1 ? VB_PAD + i * xStep : VB_W / 2,
    y: VB_PAD + (1 - v / max) * (vbH - VB_PAD * 2),
    v,
    label: labels[i] ?? String(i),
  }));

  const linePoints = pts.map((p) => `${p.x},${p.y}`).join(" ");

  const areaD =
    n === 0
      ? ""
      : [
          `M ${pts[0].x},${vbH - VB_PAD}`,
          ...pts.map((p) => `L ${p.x},${p.y}`),
          `L ${pts[n - 1].x},${vbH - VB_PAD}`,
          "Z",
        ].join(" ");

  const colorFaint = color + "22";
  const active = activeIdx !== null ? pts[activeIdx] : null;

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (n === 0) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const relX = (e.clientX - rect.left) / rect.width;
    const idx = Math.round(relX * (n - 1));
    setActiveIdx(Math.max(0, Math.min(n - 1, idx)));
  };

  if (n === 0) return null;

  // tooltip box: flip to left side when active point is in right half
  const tooltipOnRight = active ? active.x < VB_W / 2 : true;
  const tooltipX = active
    ? tooltipOnRight
      ? active.x + 6
      : active.x - 6 - 80
    : 0;
  const tooltipY = active ? Math.max(active.y - 22, 2) : 0;

  return (
    <div
      style={{
        border: "1px solid #e5e7eb",
        borderRadius: "8px",
        padding: "8px",
        background: "#fafafa",
      }}
    >
      <svg
        viewBox={`0 0 ${VB_W} ${vbH}`}
        width="100%"
        height={height}
        preserveAspectRatio="none"
        style={{ display: "block", cursor: "crosshair" }}
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setActiveIdx(null)}
      >
        {/* area fill */}
        {areaD && <path d={areaD} fill={colorFaint} />}

        {/* line */}
        {n > 1 && (
          <polyline
            points={linePoints}
            fill="none"
            stroke={color}
            strokeWidth="2"
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        )}

        {/* vertical crosshair */}
        {active && (
          <line
            x1={active.x}
            y1={VB_PAD}
            x2={active.x}
            y2={vbH - VB_PAD}
            stroke={color}
            strokeWidth="1"
            strokeDasharray="3 2"
            opacity="0.5"
          />
        )}

        {/* dots */}
        {pts.map((p, i) => {
          const isActive = i === activeIdx;
          return (
            <circle
              key={p.label}
              cx={p.x}
              cy={p.y}
              r={isActive ? 5 : 3}
              fill={p.v > 0 || isActive ? color : "transparent"}
              stroke="#fff"
              strokeWidth={isActive ? 2 : 1.5}
              style={{ transition: "r 0.1s ease" }}
            />
          );
        })}

        {/* tooltip box */}
        {active && (
          <g>
            <rect
              x={tooltipX}
              y={tooltipY}
              width="80"
              height="18"
              rx="3"
              fill="#1f2937"
              opacity="0.9"
            />
            <text
              x={tooltipX + 40}
              y={tooltipY + 12}
              textAnchor="middle"
              fill="#fff"
              fontSize="9"
              fontFamily="system-ui, sans-serif"
            >
              {active.label}: {formatAmount(active.v)}
            </text>
          </g>
        )}
      </svg>
    </div>
  );
}
