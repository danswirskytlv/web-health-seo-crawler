import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useScan } from "../state/ScanContext.jsx";
import { categoryMeta, severityClass } from "../lib/categoryMeta.js";
import { CategoryIcon, RobotIcon, RetryIcon, ChatBubbleIcon } from "./Icons.jsx";

// Build the opening question we hand to the chatbot when the user clicks
// "Continue in chat". Phrased as the user, grounded in the specific issue, so
// the chatbot (which already has the scan as context) can dive right in.
function buildChatSeed(issue) {
  const where = issue.url ? ` on ${issue.url}` : "";
  const urls = issue.details?.urls;
  if (urls?.length) {
    const sample = urls.slice(0, 8).join(", ");
    return (
      `I have a "${issue.issueType}" finding with these URLs returning 404: ${sample}` +
      (urls.length > 8 ? `, and ${urls.length - 8} more.` : ".") +
      " Can you help me understand and fix them?"
    );
  }
  return `Tell me more about the "${issue.issueType}" issue${where} and walk me through fixing it.`;
}

// Right-side slide-in panel that explains a selected issue and suggests a fix.
// The deterministic analyzer detected the issue; the AI only explains it —
// that boundary is shown explicitly via the trust label.
//
// Results are cached per-issue in ScanContext, so closing and reopening the
// drawer (or revisiting an issue) shows the saved answer instantly without
// re-calling Gemini, and switching between issues always works.
export default function AiFixDrawer({ issue, onClose }) {
  const { getAiFix } = useScan();
  const navigate = useNavigate();
  const open = !!issue;
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);

  // Fetch (or read from cache) whenever a new issue is selected. We track the
  // issue's identity so a stale async response can't overwrite a newer one.
  useEffect(() => {
    if (!issue) return;
    let cancelled = false;
    setResult(null);
    setError(null);
    setCopied(false);
    setLoading(true);
    getAiFix(issue)
      .then((r) => { if (!cancelled) setResult(r); })
      .catch((e) => { if (!cancelled) setError(e.message || "AI request failed"); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [issue, getAiFix]);

  const copyCode = () => {
    if (!result?.code_snippet) return;
    navigator.clipboard?.writeText(result.code_snippet);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  // Force a fresh AI request (used when the previous one fell back / errored).
  const retry = () => {
    if (!issue) return;
    setError(null);
    setResult(null);
    setLoading(true);
    getAiFix(issue, true)
      .then(setResult)
      .catch((e) => setError(e.message || "AI request failed"))
      .finally(() => setLoading(false));
  };

  // Jump to the chatbot, pre-seeded with a question about THIS issue. The chat
  // already has the scan as context, so it can answer immediately.
  const continueInChat = () => {
    if (!issue) return;
    const seed = buildChatSeed(issue);
    onClose?.();
    navigate("/ai", { state: { seed } });
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
                  <span style={{ color: "var(--cyan)", display: "inline-flex" }}><RobotIcon size={18} /></span> Pulse AI Assistant
                </div>
                <button className="btn" style={{ padding: "4px 10px" }} onClick={onClose}>✕</button>
              </div>
              <div style={{ marginTop: 12, fontSize: "1.1rem", fontWeight: 700 }}>
                {issue.issueType}
              </div>
              <div className="flex items-center gap-2 mt-2" style={{ flexWrap: "wrap" }}>
                <span className={"badge " + severityClass(issue.severity)}>{issue.severity}</span>
                <span className="badge"><CategoryIcon name={issue.category} size={13} /> {meta.label}</span>
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
                  <button className="btn mt-3" style={{ marginTop: 12 }} onClick={retry}><RetryIcon size={14} /> Retry AI</button>
                </div>
              )}
              {result && (
                <>
                  {result.source === "fallback" && (
                    <div className="dim flex items-center gap-2" style={{ fontSize: ".78rem", marginBottom: 10, flexWrap: "wrap" }}>
                      <span>
                        AI unavailable
                        {result.fallback_reason ? ` (${result.fallback_reason})` : ""} —
                        showing the built-in recommendation.
                      </span>
                      <button className="btn" style={{ padding: "3px 10px" }} onClick={retry}><RetryIcon size={13} /> Retry AI</button>
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

            {/* Persistent footer — always reachable, even mid-scroll. */}
            <div
              style={{
                padding: "14px 20px",
                borderTop: "1px solid var(--border)",
                display: "flex",
                flexDirection: "column",
                gap: 8,
              }}
            >
              <button
                className="btn primary"
                style={{ width: "100%", justifyContent: "center" }}
                onClick={continueInChat}
              >
                <ChatBubbleIcon size={16} /> Continue in chat
              </button>
              <div className="dim" style={{ fontSize: ".75rem", textAlign: "center" }}>
                Ask follow-up questions about this issue.
              </div>
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
