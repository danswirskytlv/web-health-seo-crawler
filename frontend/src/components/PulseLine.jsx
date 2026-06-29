// PulseLine — the EKG motif.
//
// Renders a dim baseline heart-monitor trace with a bright "signal" segment
// that travels along it (via stroke-dashoffset animation). The animation is
// gated by the global --motion token and is forced off under
// prefers-reduced-motion and print (see theme.css). The colour is the live
// accent (--signal), so it retunes with the runtime accent automatically.
//
// Reused across the app: the hero "SIGNAL · LIVE" rail, the scan-in-progress
// trace, the vitals strip, and the logo's wave.
//
// Props:
//   width / height  – viewBox proportions (the SVG scales to its container).
//   strokeBase      – baseline trace width.
//   beats           – how many QRS spikes to draw across the width.
//   className       – extra classes on the <svg>.
//   baseOnly        – render just the dim baseline (no travelling glow).

export default function PulseLine({
  width = 600,
  height = 64,
  beats = 4,
  className = "",
  baseOnly = false,
  ...rest
}) {
  const d = buildEkgPath(width, height, beats);
  return (
    <svg
      className={`pulseline ${className}`}
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      role="img"
      aria-label="signal trace"
      {...rest}
    >
      <path className="ekg-base" d={d} />
      {!baseOnly && <path className="ekg-glow" d={d} />}
    </svg>
  );
}

// Build a repeating EKG waveform: flat baseline punctuated by P-QRS-T-ish
// spikes. Kept deterministic so the baseline and glow paths match exactly.
function buildEkgPath(w, h, beats) {
  const mid = h / 2;
  const seg = w / beats;
  let d = `M0 ${mid}`;
  for (let i = 0; i < beats; i++) {
    const x = i * seg;
    // lead-in flat
    d += ` L${(x + seg * 0.18).toFixed(1)} ${mid}`;
    // small P bump
    d += ` L${(x + seg * 0.26).toFixed(1)} ${(mid - h * 0.08).toFixed(1)}`;
    d += ` L${(x + seg * 0.34).toFixed(1)} ${mid}`;
    // Q dip
    d += ` L${(x + seg * 0.40).toFixed(1)} ${(mid + h * 0.12).toFixed(1)}`;
    // R spike (tall)
    d += ` L${(x + seg * 0.46).toFixed(1)} ${(mid - h * 0.42).toFixed(1)}`;
    // S dip
    d += ` L${(x + seg * 0.52).toFixed(1)} ${(mid + h * 0.20).toFixed(1)}`;
    // back to baseline
    d += ` L${(x + seg * 0.58).toFixed(1)} ${mid}`;
    // T bump
    d += ` L${(x + seg * 0.72).toFixed(1)} ${(mid - h * 0.12).toFixed(1)}`;
    d += ` L${(x + seg * 0.82).toFixed(1)} ${mid}`;
    // tail flat
    d += ` L${(x + seg).toFixed(1)} ${mid}`;
  }
  return d;
}
