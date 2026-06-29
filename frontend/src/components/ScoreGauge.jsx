// Radial health-score gauge — the signature SitePulse visual.
// A 270° arc from 0 to 100, colored by grade, with the score + grade label
// in the center.

const GRADE_COLOR = {
  Excellent: "var(--green)",
  Good: "var(--green)",
  "Needs Improvement": "var(--amber)",
  Critical: "var(--red)",
};

function gradeForScore(score) {
  if (score >= 90) return "Excellent";
  if (score >= 75) return "Good";
  if (score >= 50) return "Needs Improvement";
  return "Critical";
}

export default function ScoreGauge({ score = 0, grade, size = 200 }) {
  const label = grade || gradeForScore(score);
  const color = GRADE_COLOR[label] || "var(--cyan)";

  // Geometry: a 270° arc (gap at the bottom).
  const stroke = 14;
  const r = (size - stroke) / 2;
  const cx = size / 2;
  const cy = size / 2;
  const startAngle = 135; // degrees
  const sweep = 270;
  const circumference = 2 * Math.PI * r;
  const arcLen = (sweep / 360) * circumference;
  const progress = Math.max(0, Math.min(100, score)) / 100;

  // Rotate so the arc starts at the bottom-left and sweeps clockwise.
  const rotate = startAngle;

  return (
    <div style={{ position: "relative", width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: `rotate(${rotate}deg)` }}>
        {/* Track */}
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${arcLen} ${circumference}`}
        />
        {/* Progress */}
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${arcLen * progress} ${circumference}`}
          style={{
            transition: "stroke-dasharray 0.8s ease",
            filter: `drop-shadow(0 0 8px ${color})`,
          }}
        />
      </svg>
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          // Nudge the stack up so a long grade label clears the bottom arc.
          paddingBottom: size * 0.08,
        }}
      >
        <div style={{ fontSize: size * 0.26, fontWeight: 800, lineHeight: 1, color: "var(--text)" }}>
          {Math.round(score)}
        </div>
        <div style={{ color: "var(--text-muted)", fontSize: size * 0.07, marginTop: 2 }}>
          / 100
        </div>
        <div
          style={{
            color,
            fontWeight: 700,
            fontSize: size * 0.075,
            marginTop: 8,
            // Keep the label on one line, centered, and clear of the arc.
            maxWidth: size * 0.82,
            textAlign: "center",
            lineHeight: 1.15,
            whiteSpace: "nowrap",
          }}
        >
          {label}
        </div>
      </div>
    </div>
  );
}
