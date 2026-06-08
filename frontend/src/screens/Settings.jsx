import { useEffect, useState } from "react";
import PageHeader from "../components/PageHeader.jsx";
import { api } from "../api.js";

export default function Settings() {
  const [health, setHealth] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.health().then(setHealth).catch((e) => setError(e.message));
  }, []);

  return (
    <>
      <PageHeader title="Settings" subtitle="Status and preferences for SitePulse." />

      <div className="grid cols-2">
        <div className="card">
          <div style={{ fontWeight: 700 }}>System status</div>
          <Row label="API">
            {error ? (
              <span style={{ color: "var(--red)" }}>● Unreachable</span>
            ) : health ? (
              <span style={{ color: "var(--green)" }}>● Connected</span>
            ) : (
              <span className="muted">checking…</span>
            )}
          </Row>
          <Row label="AI Assistant">
            {health ? (
              health.aiAvailable ? (
                <span style={{ color: "var(--green)" }}>● Gemini connected</span>
              ) : (
                <span style={{ color: "var(--amber)" }}>● Fallback mode (no API key)</span>
              )
            ) : (
              <span className="muted">—</span>
            )}
          </Row>
          {error && <div className="dim mt-2" style={{ fontSize: ".8rem" }}>{error}</div>}
        </div>

        <div className="card">
          <div style={{ fontWeight: 700 }}>About SitePulse</div>
          <p className="muted mt-2" style={{ lineHeight: 1.6 }}>
            SitePulse crawls your site, detects technical health and SEO issues with
            deterministic rules, scores them transparently, and uses AI only to
            explain and suggest fixes — never to decide whether an issue exists.
          </p>
          <span className="trust mt-3">
            Detected by <b>SitePulse Analyzer</b> · Explained by AI
          </span>
        </div>
      </div>

      <div className="card mt-3" style={{ marginTop: 18 }}>
        <div style={{ fontWeight: 700 }}>Scan defaults</div>
        <p className="muted mt-2" style={{ lineHeight: 1.6 }}>
          Set scan parameters (URL, max pages, depth, TLS and exposed-path checks)
          on the <b>Scan</b> screen each time you run a scan.
        </p>
        <div className="dim mt-2" style={{ fontSize: ".8rem" }}>
          To enable live AI explanations, set <code>GEMINI_API_KEY</code> in the
          project's <code>.env</code> file and restart the API.
        </div>
      </div>
    </>
  );
}

function Row({ label, children }) {
  return (
    <div className="flex items-center justify-between mt-2" style={{ fontSize: ".92rem" }}>
      <span className="muted">{label}</span>
      <span>{children}</span>
    </div>
  );
}
