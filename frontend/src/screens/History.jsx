import { useEffect, useMemo, useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import PageHeader from "../components/PageHeader.jsx";
import { api } from "../api.js";
import { categoryMeta, severityClass, scoreStatus } from "../lib/categoryMeta.js";
import { CategoryIcon, SparkleIcon } from "../components/Icons.jsx";

export default function History() {
  const [scans, setScans] = useState(null);
  const [error, setError] = useState(null);
  const [fromId, setFromId] = useState(null);
  const [toId, setToId] = useState(null);

  useEffect(() => {
    api
      .listScans(null, 50)
      .then((r) => setScans(r.scans))
      .catch((e) => setError(e.message));
  }, []);

  // Chart data: oldest -> newest so the line reads left to right.
  const chartData = useMemo(() => {
    if (!scans) return [];
    return [...scans]
      .reverse()
      .map((s) => ({ when: shortDate(s.scannedAt), score: s.score, issues: s.issuesCount }));
  }, [scans]);

  if (error) {
    return (
      <>
        <PageHeader title="History" subtitle="Your website's health over time." />
        <div className="card" style={{ color: "var(--red)" }}>Couldn't load history: {error}</div>
      </>
    );
  }
  if (!scans) {
    return (
      <>
        <PageHeader title="History" subtitle="Your website's health over time." />
        <div className="card muted">Loading…</div>
      </>
    );
  }
  if (scans.length === 0) {
    return (
      <>
        <PageHeader title="History" subtitle="Your website's health over time." />
        <div className="card" style={{ textAlign: "center", padding: "40px 24px" }}>
          <div className="muted">No scans yet. Run a scan from the Overview screen and it'll be saved here.</div>
        </div>
      </>
    );
  }

  return (
    <>
      <PageHeader
        title="History"
        subtitle="SitePulse keeps every scan, so you can track your site's health over time."
      />

      {/* Trend chart */}
      <div className="card" style={{ marginBottom: 18 }}>
        <div className="section-title" style={{ marginTop: 0 }}>Health Score Over Time</div>
        <div style={{ height: 240 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 0, left: -16 }}>
              <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
              <XAxis dataKey="when" stroke="var(--text-dim)" fontSize={12} tickLine={false} />
              <YAxis domain={[0, 100]} stroke="var(--text-dim)" fontSize={12} tickLine={false} />
              <Tooltip
                contentStyle={{
                  background: "var(--panel)",
                  border: "1px solid var(--border)",
                  borderRadius: 10,
                  color: "var(--text)",
                }}
              />
              <Line
                type="monotone"
                dataKey="score"
                stroke="var(--cyan)"
                strokeWidth={2.5}
                dot={{ r: 3, fill: "var(--cyan)" }}
                activeDot={{ r: 5 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Recent scans table */}
      <div className="section-title">Recent Scans</div>
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: ".9rem" }}>
          <thead>
            <tr style={{ color: "var(--text-muted)", textAlign: "left" }}>
              <Th>Date</Th><Th>Site</Th><Th>Pages</Th><Th>Score</Th><Th>Issues</Th><Th>Compare</Th>
            </tr>
          </thead>
          <tbody>
            {scans.map((s) => {
              const st = scoreStatus(s.score);
              return (
                <tr key={s.id} style={{ borderTop: "1px solid var(--border)" }}>
                  <Td>{shortDate(s.scannedAt)}</Td>
                  <Td style={{ maxWidth: 240, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {s.rootUrl}
                  </Td>
                  <Td>{s.pagesCount}</Td>
                  <Td><span style={{ color: st.color, fontWeight: 700 }}>{s.score}</span></Td>
                  <Td>{s.issuesCount}</Td>
                  <Td>
                    <div className="flex gap-2">
                      <button
                        className="btn"
                        style={{ padding: "4px 10px", borderColor: fromId === s.id ? "var(--cyan)" : "var(--border)" }}
                        onClick={() => setFromId(s.id)}
                      >
                        From
                      </button>
                      <button
                        className="btn"
                        style={{ padding: "4px 10px", borderColor: toId === s.id ? "var(--cyan)" : "var(--border)" }}
                        onClick={() => setToId(s.id)}
                      >
                        To
                      </button>
                    </div>
                  </Td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="dim mt-2" style={{ fontSize: ".82rem" }}>
        Pick an older scan as <b>From</b> and a newer one as <b>To</b> to compare them.
      </div>

      {fromId && toId && fromId !== toId && <CompareView fromId={fromId} toId={toId} />}
    </>
  );
}

/* --- Compare view ---------------------------------------------------- */

function CompareView({ fromId, toId }) {
  const [diff, setDiff] = useState(null);
  const [error, setError] = useState(null);
  const [insight, setInsight] = useState(null);
  const [loadingInsight, setLoadingInsight] = useState(false);

  useEffect(() => {
    setDiff(null);
    setInsight(null);
    setError(null);
    api.diff(fromId, toId).then(setDiff).catch((e) => setError(e.message));
  }, [fromId, toId]);

  const getInsight = () => {
    setLoadingInsight(true);
    api
      .aiRootCause(fromId, toId)
      .then(setInsight)
      .catch((e) => setError(e.message))
      .finally(() => setLoadingInsight(false));
  };

  if (error) return <div className="card mt-3" style={{ color: "var(--red)" }}>{error}</div>;
  if (!diff) return <div className="card mt-3 muted">Loading comparison…</div>;

  const delta = diff.scoreDelta;
  return (
    <div className="card" style={{ marginTop: 18 }}>
      <div className="section-title" style={{ marginTop: 0 }}>Comparison</div>

      <div className="grid cols-4" style={{ marginBottom: 14 }}>
        <Stat label="Score change"
          value={`${diff.fromScan.score} → ${diff.toScan.score}`}
          sub={`${delta >= 0 ? "+" : ""}${delta}`}
          color={delta >= 0 ? "var(--green)" : "var(--red)"} />
        <Stat label="Resolved" value={diff.fixedIssues.length} color="var(--green)" />
        <Stat label="New" value={diff.newIssues.length} color="var(--red)" />
        <Stat label="Still open" value={diff.unchangedIssues.length} />
      </div>

      {/* AI root-cause */}
      <div className="card" style={{ background: "rgba(34,211,238,0.04)", marginBottom: 14 }}>
        <div className="flex items-center justify-between" style={{ flexWrap: "wrap", gap: 8 }}>
          <div className="flex items-center gap-2" style={{ fontWeight: 700 }}>
            <span style={{ color: "var(--cyan)", display: "inline-flex" }}><SparkleIcon size={16} /></span>
            Root-Cause Analysis
          </div>
          <button className="btn primary" onClick={getInsight} disabled={loadingInsight}>
            {loadingInsight ? "Analyzing…" : "Get AI Insights"}
          </button>
        </div>
        {insight && (
          <div className="mt-3">
            {insight.source === "fallback" && (
              <div className="dim" style={{ fontSize: ".78rem", marginBottom: 6 }}>
                AI unavailable — basic summary shown.
              </div>
            )}
            <P label="What changed" text={insight.summary} />
            <P label="Likely cause" text={insight.likelyCause} />
            <P label="Recommended action" text={insight.recommendedAction} />
          </div>
        )}
      </div>

      <IssueList title="New issues" issues={diff.newIssues} empty="No new issues — nice." />
      <IssueList title="Resolved" issues={diff.fixedIssues} empty="Nothing was resolved between these scans." />
      <IssueList title="Still open" issues={diff.unchangedIssues} empty="No issues carried over." />
    </div>
  );
}

function IssueList({ title, issues, empty }) {
  return (
    <div style={{ marginTop: 14 }}>
      <div style={{ fontWeight: 700, fontSize: ".92rem", marginBottom: 8 }}>{title} ({issues.length})</div>
      {issues.length === 0 ? (
        <div className="dim" style={{ fontSize: ".85rem" }}>{empty}</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {issues.slice(0, 30).map((i, idx) => {
            const meta = categoryMeta(i.category);
            return (
              <div key={idx} className="flex items-center gap-2" style={{ fontSize: ".85rem", flexWrap: "wrap" }}>
                <span className={"badge " + severityClass(i.severity)}>{i.severity}</span>
                <span className="muted flex items-center gap-2"><CategoryIcon name={i.category} size={13} /> {i.issueType}</span>
                <span className="dim" style={{ wordBreak: "break-all" }}>{i.url}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* --- small helpers --------------------------------------------------- */

const Th = ({ children }) => <th style={{ padding: "12px 14px", fontWeight: 600 }}>{children}</th>;
const Td = ({ children, style }) => <td style={{ padding: "11px 14px", ...style }}>{children}</td>;

function Stat({ label, value, sub, color }) {
  return (
    <div className="card" style={{ padding: "12px 14px" }}>
      <div className="dim" style={{ fontSize: ".76rem" }}>{label}</div>
      <div style={{ fontSize: "1.2rem", fontWeight: 800, marginTop: 4, color: color || "var(--text)" }}>{value}</div>
      {sub != null && <div style={{ fontSize: ".8rem", color: color || "var(--text-muted)" }}>{sub}</div>}
    </div>
  );
}
function P({ label, text }) {
  if (!text) return null;
  return (
    <div style={{ marginBottom: 8 }}>
      <span style={{ fontWeight: 700, fontSize: ".88rem" }}>{label}: </span>
      <span className="muted">{text}</span>
    </div>
  );
}
function shortDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  return d.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}
