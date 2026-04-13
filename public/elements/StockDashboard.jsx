import { useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Progress } from "@/components/ui/progress";

// ── Colour palette per metric label ──────────────────────────────────────────
const METRIC_COLOURS = {
  "Close Price": { bar: "#38bdf8", glow: "rgba(56,189,248,0.25)",  hover: "#7dd3fc" },
  "Daily High":  { bar: "#34d399", glow: "rgba(52,211,153,0.25)",  hover: "#6ee7b7" },
  "Daily Low":   { bar: "#fb7185", glow: "rgba(251,113,133,0.25)", hover: "#fda4af" },
  "Open Price":  { bar: "#fbbf24", glow: "rgba(251,191,36,0.25)",  hover: "#fde68a" },
  "Volume":      { bar: "#a78bfa", glow: "rgba(167,139,250,0.25)", hover: "#c4b5fd" },
};
const DEFAULT_COLOUR = { bar: "#38bdf8", glow: "rgba(56,189,248,0.25)", hover: "#7dd3fc" };

// ── Bar chart renderer ────────────────────────────────────────────────────────
function BarChartNode({ node, label }) {
  const [hovered, setHovered] = useState(null);

  const data   = node?.data   ?? [];
  const series = node?.series ?? [];
  if (!data.length || !series.length) {
    return <p className="text-muted-foreground text-xs">No data</p>;
  }

  const colours = METRIC_COLOURS[label] ?? DEFAULT_COLOUR;
  const W = 520, H = node.height ?? 220;
  const padL = 52, padR = 16, padT = 16, padB = 40;
  const plotW = W - padL - padR;
  const plotH = H - padT - padB;

  // Handle both camelCase and snake_case serialisation from prefab-ui
  const xKey = node.xAxis ?? node.x_axis ?? "Date";
  const yKey = (series[0]?.dataKey ?? series[0]?.data_key ?? "Close");

  const maxVal  = Math.max(...data.map(d => Number(d[yKey]) || 0)) || 1;
  const niceMax = maxVal < 1000    ? Math.ceil(maxVal / 10) * 10
                : maxVal < 100000  ? Math.ceil(maxVal / 1000) * 1000
                : Math.ceil(maxVal / 10000000) * 10000000;

  const slotW  = plotW / data.length;
  const barW   = Math.max(3, slotW * 0.55);
  const toY    = v => padT + plotH - (v / niceMax) * plotH;
  const fmt    = v => v >= 1e9 ? (v/1e9).toFixed(1)+"B"
                    : v >= 1e6 ? (v/1e6).toFixed(1)+"M"
                    : v >= 1e3 ? (v/1e3).toFixed(0)+"k"
                    : String(Math.round(v));

  const skipEvery = Math.ceil(data.length / 10);

  return (
    <div className="w-full overflow-x-auto">
      <svg viewBox={`0 0 ${W} ${H}`} style={{ display: "block", width: "100%" }}>
        {/* Grid */}
        {[0,1,2,3,4].map(i => {
          const val = (niceMax / 4) * i;
          const y   = toY(val);
          return (
            <g key={i}>
              <line x1={padL} y1={y} x2={W-padR} y2={y} stroke="rgba(255,255,255,0.07)" strokeDasharray="4 5" />
              <text x={padL-6} y={y+4} textAnchor="end" fill="rgba(255,255,255,0.4)" fontSize={9}>{fmt(val)}</text>
            </g>
          );
        })}
        {/* Baseline */}
        <line x1={padL} y1={padT+plotH} x2={W-padR} y2={padT+plotH} stroke="rgba(255,255,255,0.12)" />

        {/* Bars */}
        {data.map((d, i) => {
          const val = Number(d[yKey]) || 0;
          const bh  = (val / niceMax) * plotH;
          const cx  = padL + i * slotW + slotW / 2;
          const x   = cx - barW / 2;
          const y   = toY(val);
          const r   = Math.min(3, bh / 2);
          const isH = hovered === i;

          const pathD = bh > 0 ? [
            `M ${x} ${y+r}`, `Q ${x} ${y} ${x+r} ${y}`,
            `L ${x+barW-r} ${y}`, `Q ${x+barW} ${y} ${x+barW} ${y+r}`,
            `L ${x+barW} ${y+bh}`, `L ${x} ${y+bh}`, "Z",
          ].join(" ") : "";

          return (
            <g key={i} onMouseEnter={() => setHovered(i)} onMouseLeave={() => setHovered(null)}>
              {bh > 0 && <path d={pathD} fill={colours.glow} style={{ filter: "blur(4px)" }} />}
              {bh > 0 && <path d={pathD} fill={isH ? colours.hover : colours.bar} style={{ transition: "fill 0.12s" }} />}
              {isH && bh > 0 && (
                <text x={cx} y={Math.max(y-5, padT+10)} textAnchor="middle" fill="white" fontSize={9} fontWeight={600}>
                  {fmt(val)}
                </text>
              )}
              {i % skipEvery === 0 && (
                <text x={cx} y={H-padB+16} textAnchor="middle" fill="rgba(255,255,255,0.4)" fontSize={8}>
                  {String(d[xKey] ?? "")}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}

// ── Recursive Prefab node renderer ───────────────────────────────────────────
function PrefabNode({ node, depth }) {
  if (!node || typeof node !== "object") return null;
  const kids = (node.children ?? []).map((c, i) => <PrefabNode key={i} node={c} depth={(depth??0)+1} />);
  const cls  = node.cssClass ?? node.css_class ?? "";

  switch (node.type) {
    case "Column":
      return <div className={cls} style={{ display:"flex", flexDirection:"column", gap:14 }}>{kids}</div>;
    case "Row":
      return <div className={cls} style={{ display:"flex", flexDirection:"row", flexWrap:"wrap", gap:12 }}>{kids}</div>;
    case "Grid": {
      const cols = typeof node.columns === "number" ? node.columns : 2;
      return (
        <div className={cls} style={{ display:"grid", gridTemplateColumns:`repeat(${cols}, minmax(0,1fr))`, gap:14 }}>
          {kids}
        </div>
      );
    }
    case "Div":
      return <div className={cls}>{kids}</div>;
    case "Heading": {
      const sz = [null,22,18,15,13][Math.min(node.level??2,4)];
      return <p style={{ fontSize:sz, fontWeight:600, color:"rgba(255,255,255,0.9)", margin:"0 0 2px" }}>{node.content}</p>;
    }
    case "Text": case "Paragraph":
      return <p style={{ fontSize:13, color:"rgba(255,255,255,0.8)", margin:0 }}>{node.content}</p>;
    case "Muted":
      return <p style={{ fontSize:12, color:"rgba(255,255,255,0.45)", margin:0 }}>{node.content}</p>;
    case "Card":
      return (
        <div className={cls} style={{
          background:"rgba(255,255,255,0.04)", border:"1px solid rgba(255,255,255,0.09)",
          borderRadius:12, overflow:"hidden",
        }}>{kids}</div>
      );
    case "CardHeader":
      return <div style={{ padding:"12px 16px 6px", borderBottom:"1px solid rgba(255,255,255,0.06)" }}>{kids}</div>;
    case "CardTitle":
      return <p style={{ fontSize:12, fontWeight:600, color:"rgba(255,255,255,0.7)", margin:0 }}>{node.content ?? kids}</p>;
    case "CardContent":
      return <div className={cls} style={{ padding:"10px 16px 14px" }}>{kids}</div>;
    case "Separator":
      return <hr style={{ border:"none", borderTop:"1px solid rgba(255,255,255,0.09)", margin:"2px 0" }} />;
    case "Loader":
      return (
        <svg width={18} height={18} viewBox="0 0 24 24" style={{ animation:"spin 1s linear infinite", display:"inline-block" }}>
          <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
          <circle cx={12} cy={12} r={10} stroke="rgba(255,255,255,0.15)" strokeWidth={3} fill="none" />
          <path d="M12 2a10 10 0 0 1 10 10" stroke="#38bdf8" strokeWidth={3} fill="none" strokeLinecap="round" />
        </svg>
      );
    case "BarChart": {
      const seriesLabel = (node.series??[])[0]?.label ?? (node.series??[])[0]?.dataKey ?? "";
      return <BarChartNode node={node} label={seriesLabel} />;
    }
    default:
      if (kids.length) return <div className={cls}>{kids}</div>;
      if (node.content) return <span style={{ fontSize:13, color:"rgba(255,255,255,0.7)" }}>{node.content}</span>;
      return null;
  }
}

// ── Root — props injected globally by Chainlit, never as function arg ─────────
export default function StockDashboard() {
  // props is the raw structured_content dict:
  // { "$prefab": {...}, "view": { type, children, ... }, "state": {...} }
  const view = props?.view;

  if (!view) {
    return (
      <Card className="w-full border-destructive/30 bg-destructive/5">
        <CardContent className="pt-4 text-destructive text-sm">
          StockDashboard: missing <code>view</code> in props.<br />
          Received keys: <code>{JSON.stringify(Object.keys(props ?? {}))}</code>
        </CardContent>
      </Card>
    );
  }

  return (
    <div style={{
      width:"100%", borderRadius:16,
      border:"1px solid rgba(255,255,255,0.08)",
      background:"rgba(255,255,255,0.025)",
      backdropFilter:"blur(16px)",
      boxShadow:"0 0 40px rgba(0,0,0,0.4)",
      padding:20,
      fontFamily:"system-ui,-apple-system,sans-serif",
    }}>
      <PrefabNode node={view} depth={0} />
    </div>
  );
}
