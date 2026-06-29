import Logo from "./Logo.jsx";
import PulseLine from "./PulseLine.jsx";

// HeroLockup — the centered, prominent brand lockup used on the landing /
// entry hero: the pulse mark beside a large "Site / Pulse" wordmark (Pulse in
// signal cyan), with the EKG "BPM · 72  /  SIGNAL · LIVE" rail beneath it.
//
// Props:
//   bpm  – number shown in the left caption (default 72).
//   markSize – pixel size of the logo mark.
export default function HeroLockup({ bpm = 72, markSize = 48 }) {
  return (
    <div className="hero-lockup">
      <div className="mark-row">
        <Logo size={markSize} />
        <span className="wordmark-xl">
          <span className="site">Site</span>
          <span className="pulse">Pulse</span>
        </span>
      </div>

      {/* EKG signal rail */}
      <div className="signal-rail">
        <span className="cap">
          BPM · <b>{bpm}</b>
        </span>
        <PulseLine height={48} beats={5} />
        <span className="cap" style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
          SIGNAL · <b>LIVE</b>
          <span className="live-dot" />
        </span>
      </div>
    </div>
  );
}
