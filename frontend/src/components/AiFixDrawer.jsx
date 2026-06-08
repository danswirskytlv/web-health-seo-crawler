import { useEffect, useState } from "react";
import { api } from "../api.js";
import { categoryMeta, severityClass } from "../lib/categoryMeta.js";

// Right-side slide-in panel that explains a selected issue and suggests a fix.
// The deterministic analyzer detected the issue; the AI only explains it —
// that boundary is shown explicitly via the trust label.
export default function AiFixDrawer({ issue, onClose }) {
  const open = !!issue;
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);

  // Reset + fetch whenever a new issue is selected.
  useEffect(() => {
    if (!issue) return;
    setResult(null);
    setError(null);
    setCopied(false);
    setLoading(true);
    api
      .aiFix(issue)
      .then(setResult)
      .catch((e) => setError(e.message || "AI request failed"))
      .finally(() => setLoading(false));
  }, [issue]);

  const copyCode = () => {
    if (!result?.code_snippet) return;
    navigator.clipboard?.writeText(result.code_snippet);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const meta = issue ? categoryMeta(issue.category) : null;

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: "fixed",
          inset: 0,
          background: "rgba(2,6,16,0.55)",
          backdropFilter: "blur(2px)",
          opacity: open ? 1 : 0,
          pointerEvents: open ? "auto" : "none",
          transition: "opacity 0.2s ease",
          zIndex: 40,
        }}
      />
      {/* Drawer */}
      <aside
        style={{
          position: "fixed",
          top: 0,
          right: 0,
          height: "100vh",
          width: "min(460px, 92vw)",
          background: "var(--panel)",
          borderLeft: "1px solid var(--border)",
          boxShadow: "-20px 0 50px rgba(0,0,0,0.4)",
          transform: open ? "translateX(0)" : "translateX(100%)",
          transition: "transform 0.25s ease",
          zIndex: 50,
          display: "flex",
          flexDirection: "column",
        }}
      >
        {issue && (
          <>
            <div style={{ padding: "18px 20px", borderBottom: "1px solid var(--border)" }}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2" style={{ fontWeight: 700 }}>
                  <span>🤖</span> Pulse AI Assistant
                </div>
                <button className="btn" style={{ padding: "4px 10px" }} onClick={onClose}>✕</button>
              </div>
              <div style={{ marginTop: 12, fontSize: "1.1rem", fontWeight: 700 }}>
                {issue.issueType}
              </div>
              <div className="flex items-center gap-2 mt-2" style={{ flexWrap: "wrap" }}>
                <span className={"badge " + severityClass(issue.severity)}>{issue.severity}</span>
                <span className="badge">{meta.icon} {meta.label}</span>
              </div>
              <div className="muted mt-2" style={{ fontSize: ".82rem", wordBreak: "break-all" }}>
                {issue.url}
              </div>
              <span className="trust mt-3">
                Detected by <b>SitePulse Analyzer</b> · Explained by AI
              </span>
            </div>

            <div style={{ padding: "18px 20px", overflowY: "auto", flex: 1 }}>
              {loading && (
                <div className="flex items-center gap-2 muted">
                  <span className="pulse-dot" /> Asking the AI…
                </div>
              )}
              {error && (
                <div style={{ color: "var(--red)" }}>
                  Couldn't reach the AI ({error}). The rule-based recommendation:
                  <div className="muted mt-2">{issue.recommendation}</div>
                </div>
              )}
              {result && (
                <>
                  {result.source === "fallback" && (
                    <div className="dim" style={{ fontSize: ".78rem", marginBottom: 10 }}>
                      AI unavailable — showing the built-in recommendation.
                    </div>
                  )}
                  <Section title="What was found">{result.simple_explanation}</Section>
                  <Section title="Why it matters">{result.why_it_matters}</Section>
                  <Section title="How to fix it">{result.suggested_fix}</Section>
                  {result.code_snippet && (
                    <div style={{ marginTop: 16 }}>
                      <div className="flex items-center justify-between">
                        <div style={{ fontWeight: 700, fontSize: ".9rem" }}>Suggested code</div>
                        <button className="btn" style={{ padding: "4px 10px" }} onClick={copyCode}>
                          {copied ? "✓ Copied" : "Copy"}
                        </button>
                      </div>
                      <pre
                        style={{
                          marginTop: 8,
                          background: "var(--bg)",
                          border: "1px solid var(--border)",
                          borderRadius: 12,
                          padding: 14,
                          overflowX: "auto",
                          fontSize: ".84rem",
                          color: "var(--cyan)",
                        }}
                      >
                        <code>{result.code_snippet}</code>
                      </pre>
                    </div>
                  )}
                </>
              )}
            </div>
          </>
        )}
      </aside>
    </>
  );
}

function Section({ title, children }) {
  if (!children) return null;
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ fontWeight: 700, fontSize: ".9rem", marginBottom: 4 }}>{title}</div>
      <div className="muted" style={{ lineHeight: 1.6 }}>{children}</div>
    </div>
  );
}
