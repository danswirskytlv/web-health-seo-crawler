import { useState } from "react";
import { useNavigate } from "react-router-dom";
import PageHeader from "../components/PageHeader.jsx";
import { useScan } from "../state/ScanContext.jsx";

export default function Scan() {
  const { runScan, status } = useScan();
  const navigate = useNavigate();
  const [opts, setOpts] = useState({
    url: "http://localhost:8000",
    maxPages: 50,
    maxDepth: 2,
    checkTls: true,
    checkExposedPaths: false,
    respectRobots: true,
  });

  const set = (k, v) => setOpts((o) => ({ ...o, [k]: v }));

  const start = async () => {
    if (!opts.url.trim()) return;
    try {
      await runScan({ ...opts, save: true });
      navigate("/"); // jump to the Overview to see results
    } catch {
      /* error shown on Overview */
    }
  };

  return (
    <>
      <PageHeader title="Scan" subtitle="Configure and run a website health scan." />

      <div className="card" style={{ maxWidth: 640 }}>
        <Label>Website URL</Label>
        <input className="input" value={opts.url} onChange={(e) => set("url", e.target.value)}
          placeholder="https://example.com" />

        <div className="grid cols-2 mt-3" style={{ gap: 14 }}>
          <div>
            <Label>Max pages: {opts.maxPages}</Label>
            <input type="range" min="5" max="200" value={opts.maxPages}
              onChange={(e) => set("maxPages", Number(e.target.value))} style={{ width: "100%" }} />
          </div>
          <div>
            <Label>Max depth: {opts.maxDepth}</Label>
            <input type="range" min="1" max="5" value={opts.maxDepth}
              onChange={(e) => set("maxDepth", Number(e.target.value))} style={{ width: "100%" }} />
          </div>
        </div>

        <div className="mt-3" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <Toggle label="Respect robots.txt" checked={opts.respectRobots} onChange={(v) => set("respectRobots", v)} />
          <Toggle label="Check TLS certificates (live)" checked={opts.checkTls} onChange={(v) => set("checkTls", v)} />
          <Toggle
            label="Probe for exposed sensitive paths"
            help="Active check — only use on sites you own."
            checked={opts.checkExposedPaths}
            onChange={(v) => set("checkExposedPaths", v)}
          />
        </div>

        <button className="btn primary mt-3" style={{ marginTop: 18 }} onClick={start} disabled={status === "running"}>
          {status === "running" ? "Scanning…" : "📡 Run Health Scan"}
        </button>
        <div className="dim mt-2" style={{ fontSize: ".8rem" }}>
          Polite crawling enabled — SitePulse scans responsibly.
        </div>
      </div>
    </>
  );
}

const Label = ({ children }) => (
  <div style={{ fontWeight: 600, fontSize: ".85rem", marginBottom: 6, color: "var(--text-muted)" }}>{children}</div>
);

function Toggle({ label, help, checked, onChange }) {
  return (
    <label className="flex items-center gap-2" style={{ cursor: "pointer" }}>
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span>
        {label}
        {help && <span className="dim" style={{ fontSize: ".78rem", marginLeft: 6 }}>{help}</span>}
      </span>
    </label>
  );
}
