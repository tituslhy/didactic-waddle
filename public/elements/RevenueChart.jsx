export default function RevenueChart() {
  const sc = props;

  if (!sc) {
    return (
      <div className="text-red-300 text-sm p-4 border border-red-500/20 rounded-lg bg-red-500/5">
        RevenueChart: missing props
      </div>
    );
  }

  const view = sc?.view;
  if (!view) {
    return (
      <div className="text-red-300 text-sm p-4 border border-red-500/20 rounded-lg bg-red-500/5">
        RevenueChart: missing view
      </div>
    );
  }

  const titleNode = view?.children?.find(n => n.type === "Heading");

  function BarChartNode({ node }) {
    const data = node?.data || [];
    const series = node?.series || [];

    if (!data.length || !series.length) {
      return <div className="text-white/60 text-sm">No data</div>;
    }

    const width = 520;
    const height = node.height || 320;
    const padding = 44;

    const keyX = node.xAxis;
    const keyY = series[0].dataKey;

    const maxVal = Math.max(...data.map(d => d[keyY] ?? 0)) || 1;
    const slotWidth = (width - padding * 2) / data.length;
    const barWidth = slotWidth * 0.55;

    const ticks = 4;
    const tickValues = Array.from({ length: ticks + 1 }, (_, i) => (maxVal * i) / ticks);

    return (
      <div className="relative mt-4">
        <svg
          width="100%"
          viewBox={`0 0 ${width} ${height}`}
          className="overflow-visible"
        >
          {/* Soft grid */}
          {Array.from({ length: 5 }).map((_, i) => {
            const y = padding + (i * (height - padding * 2)) / 4;

            return (
              <line
                key={i}
                x1={padding}
                x2={width - padding}
                y1={y}
                y2={y}
                stroke="rgba(255,255,255,0.06)"
                strokeDasharray="4 6"
              />
            );
          })}

          {/* Axes */}
          <line
            x1={padding}
            y1={height - padding}
            x2={width - padding}
            y2={height - padding}
            stroke="rgba(255,255,255,0.12)"
          />
          <line
            x1={padding}
            y1={padding}
            x2={padding}
            y2={height - padding}
            stroke="rgba(255,255,255,0.12)"
          />

          {/* Y Axis Labels */}
          {tickValues.map((v, i) => {
            const y = height - padding - (v / maxVal) * (height - padding * 2);

            return (
              <text
                key={i}
                x={padding - 10}
                y={y + 4}
                textAnchor="end"
                className="text-[11px] fill-white/60"
              >
                {Math.round(v / 1000)}k
              </text>
            );
          })}

          {/* Bars */}
          {data.map((d, i) => {
            const val = d[keyY] ?? 0;
            const h = (val / maxVal) * (height - padding * 2);

            const x = padding + i * slotWidth + slotWidth * 0.2;
            const y = height - padding - h;

            return (
              <g key={i}>
                {/* Glow layer */}
                <rect
                  x={x}
                  y={y}
                  width={barWidth}
                  height={h}
                  rx="10"
                  fill="rgba(56,189,248,0.25)"
                  filter="blur(6px)"
                  className="transition-all duration-300 opacity-70"
                />

                {/* Main bar */}
                <rect
                  x={x}
                  y={y}
                  width={barWidth}
                  height={h}
                  rx="10"
                  fill="rgba(56,189,248,0.9)"
                  className="
                    transition-all duration-300
                    hover:fill-cyan-300
                    hover:drop-shadow-[0_0_12px_rgba(34,211,238,0.8)]
                    origin-bottom
                    animate-[grow_0.6s_ease-out_forwards]
                  "
                />

                {/* X labels */}
                <text
                  x={x + barWidth / 2}
                  y={height - padding + 18}
                  textAnchor="middle"
                  className="text-[11px] fill-white/60"
                >
                  {d[keyX]}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Animation keyframes */}
        <style>{`
          @keyframes grow {
            from { transform: scaleY(0); transform-origin: bottom; }
            to { transform: scaleY(1); transform-origin: bottom; }
          }
        `}</style>
      </div>
    );
  }

  // -----------------------------
  // Recursive renderer
  // -----------------------------
  function renderNode(node, i = 0) {
    if (!node) return null;

    const children = (node.children ?? []).map((c, idx) =>
      renderNode(c, idx)
    );

    switch (node.type) {
      case "Div":
        return (
          <div key={i} className={node.cssClass ?? ""}>
            {children}
          </div>
        );

      case "Column":
        return (
          <div key={i} className={node.cssClass ?? ""}>
            {children}
          </div>
        );

      case "Row":
        return (
          <div key={i} className={node.cssClass ?? ""}>
            {children}
          </div>
        );

      case "Heading":
        return (
          <h1 key={i} className="text-xl font-semibold text-white/90 mb-2">
            {node.content}
          </h1>
        );

      case "BarChart":
        return <BarChartNode key={i} node={node} />;

      default:
        return children;
    }
  }

  return (
    <div
      className="
        w-full rounded-2xl
        border border-white/10
        bg-white/5 backdrop-blur-xl
        shadow-[0_0_40px_rgba(0,0,0,0.4)]
        p-6
      "
    >
      {titleNode && (
        <div className="mb-4">
          <div className="text-lg font-semibold text-white/90">
            {titleNode.content}
          </div>
          <div className="h-px w-full bg-white/10 mt-2" />
        </div>
      )}

      {renderNode(view)}
    </div>
  );
}