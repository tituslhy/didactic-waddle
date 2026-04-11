import { useState, useMemo } from "react";

const COLOURS = [
  "#6366f1", "#22c55e", "#f59e0b", "#ef4444", "#14b8a6", "#f97316",
];

function BarChart({ node }) {
  const [hovered, setHovered] = useState(null);

  const data     = node.data      ?? [];
  const series   = node.series    ?? [];
  const xKey     = node.xAxis     ?? "x";
  const showGrid = node.showGrid  !== false;
  const showY    = node.showYAxis !== false;
  const radius   = node.barRadius ?? 4;

  if (!data.length || !series.length) return <p>No chart data.</p>;

  const W         = 560;
  const H         = node.height ?? 300;
  const padTop    = 24;
  const padBottom = 52;
  const padLeft   = showY ? 58 : 12;
  const padRight  = 20;
  const plotW     = W - padLeft - padRight;
  const plotH     = H - padTop - padBottom;

  const firstKey  = series[0].dataKey;
  const maxVal    = Math.max(...data.map(d => d[firstKey] ?? 0));
  const niceMax   = Math.ceil(maxVal / 10000) * 10000 || 1;
  const barGroup  = plotW / data.length;
  const barW      = Math.max(8, barGroup * 0.55);
  const numTicks  = 5;
  const toY       = v => padTop + plotH - (v / niceMax) * plotH;
  const fmt       = v => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v);

  return (
    <div style={{ width: "100%", overflowX: "auto" }}>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ display: "block", width: "100%" }}>
        {Array.from({ length: numTicks + 1 }, (_, i) => {
          const val = (niceMax / numTicks) * i;
          const y   = toY(val);
          return (
            <g key={i}>
              {showGrid && <line x1={padLeft} y1={y} x2={W - padRight} y2={y} stroke="#e5e7eb" strokeWidth={1} />}
              {showY && (
                <text x={padLeft - 6} y={y + 4} textAnchor="end" fill="#6b7280" fontSize={11}>
                  {fmt(val)}
                </text>
              )}
            </g>
          );
        })}

        {data.map((d, i) => {
          const cx = padLeft + i * barGroup + barGroup / 2;
          return (
            <g key={i}>
              {series.map((s, si) => {
                const val   = d[s.dataKey] ?? 0;
                const bh    = (val / niceMax) * plotH;
                const x     = cx - barW / 2;
                const y     = toY(val);
                const r     = Math.min(radius, bh / 2);
                const fill  = COLOURS[si % COLOURS.length];
                const key   = `${i}-${si}`;
                const pathD = [
                  `M ${x} ${y + r}`,
                  `Q ${x} ${y} ${x + r} ${y}`,
                  `L ${x + barW - r} ${y}`,
                  `Q ${x + barW} ${y} ${x + barW} ${y + r}`,
                  `L ${x + barW} ${y + bh}`,
                  `L ${x} ${y + bh}`,
                  "Z",
                ].join(" ");
                return (
                  <path
                    key={key}
                    d={pathD}
                    fill={fill}
                    opacity={hovered === key ? 1 : 0.88}
                    onMouseEnter={() => setHovered(key)}
                    onMouseLeave={() => setHovered(null)}
                    style={{ cursor: "default", transition: "opacity 0.15s" }}
                  />
                );
              })}
              <text
                x={cx}
                y={Math.max(toY(d[firstKey] ?? 0) - 6, padTop + 12)}
                textAnchor="middle"
                fill="#374151"
                fontSize={11}
                fontWeight={600}
              >
                {fmt(d[firstKey] ?? 0)}
              </text>
              <text x={cx} y={H - padBottom + 18} textAnchor="middle" fill="#6b7280" fontSize={12}>
                {String(d[xKey] ?? "")}
              </text>
            </g>
          );
        })}

        <line x1={padLeft} y1={padTop + plotH} x2={W - padRight} y2={padTop + plotH} stroke="#d1d5db" strokeWidth={1} />

        {series.length > 1 && series.map((s, i) => (
          <g key={i}>
            <rect x={padLeft + i * 120} y={H - 14} width={10} height={10} rx={2} fill={COLOURS[i % COLOURS.length]} />
            <text x={padLeft + i * 120 + 14} y={H - 5} fill="#374151" fontSize={11}>
              {s.label ?? s.dataKey}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}

function PrefabNode({ node }) {
  if (!node || typeof node !== "object") return null;
  const { type, children, cssClass } = node;
  const kids = (children ?? []).map((c, i) => <PrefabNode key={i} node={c} />);

  switch (type) {
    case "Div":
      return <div className={cssClass ?? ""}>{kids}</div>;
    case "Column":
      return <div className={cssClass ?? ""} style={{ display: "flex", flexDirection: "column" }}>{kids}</div>;
    case "Row":
      return <div className={cssClass ?? ""} style={{ display: "flex", flexDirection: "row", flexWrap: "wrap" }}>{kids}</div>;
    case "Heading": {
      const level = Math.min(node.level ?? 1, 6);
      const Tag = `h${level}`;
      return <Tag>{node.content ?? ""}</Tag>;
    }
    case "Text":
    case "Paragraph":
      return <p>{node.content ?? ""}</p>;
    case "BarChart":
      return <BarChart node={node} />;
    default:
      return kids.length ? <div className={cssClass ?? ""}>{kids}</div> : null;
  }
}

// Chainlit CustomElement forwards data via `props.content` (a JSON string),
// not via arbitrary props keys — parse it out here.
export default function PrefabView(props) {
  const sc = useMemo(() => {
    try {
      return typeof props.content === "string" ? JSON.parse(props.content) : null;
    } catch {
      return null;
    }
  }, [props.content]);

  if (!sc) {
    return (
      <div style={{ color: "#dc2626", fontSize: 14, padding: "0.5rem" }}>
        PrefabView: could not parse content.<br />
        Props keys: {JSON.stringify(Object.keys(props))}<br />
        Content type: {typeof props.content}
      </div>
    );
  }

  const { view } = sc;
  if (!view) {
    return <p style={{ color: "#dc2626", fontSize: 14 }}>PrefabView: no "view" key in content.</p>;
  }

  return (
    <div style={{
      fontFamily: "system-ui, -apple-system, sans-serif",
      color: "#111",
      padding: "1.25rem 1.5rem",
      border: "0.5px solid #e5e7eb",
      borderRadius: 12,
      background: "#fff",
    }}>
      <PrefabNode node={view} />
    </div>
  );
}
