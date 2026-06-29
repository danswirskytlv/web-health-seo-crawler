import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import PageHeader from "../components/PageHeader.jsx";
import ScoreGauge from "../components/ScoreGauge.jsx";
import PulseLine from "../components/PulseLine.jsx";
import HeroLockup from "../components/HeroLockup.jsx";
import {
  CategoryIcon,
  DocIcon,
  WarningIcon,
  LinkIcon,
  ClockIcon,
  DotAlertIcon,
  SparkleIcon,
  RadarIcon,
  BulbIcon,
  RobotIcon,
  ArrowRightIcon,
  CelebrateIcon,
} from "../components/Icons.jsx";
import { useScan } from "../state/ScanContext.jsx";
import { api } from "../api.js";
import { categoryMeta, scoreStatus } from "../lib/categoryMeta.js";
import { humanize } from "../lib/humanize.js";

const SCAN_STEPS = [
  "Crawling pages…",
  "Analyzing SEO signals…",
  "Checking links & security…",
  "Preparing AI explanations…",
  "Finalizing results…",
];

export default function Overview() {
  const { scan, status, error, lastScanAt, runScan } = useScan();
  const [url, setUrl] = useState("http://localhost:8000");
  const [prev, setPrev] = useState(null); // previous scan summary for trends

  // After a scan, fetch the prior scan of the same site for trend deltas.
  useEffect(() => {
    if (!scan) return;
    api
      .listScans(scan.rootUrl, 2)
      .then((r) => {
        // [newest, previous] — the previous one is index 1.
        setPrev(r.scans && r.scans.length > 1 ? r.scans[1] : null);
      })
      .catch(() => setPrev(null));
  }, [scan]);

  const onScan = () => {
    if (!url.trim()) return;
    runScan({ url: url.trim(), checkTls: true, save: true }).catch(() => {});
  };

  const lastLabel = lastScanAt && `Last scan: ${timeAgo(lastScanAt)}`;

  return (
    <>
      <PageHeader
        title="SitePulse Dashboard"
        subtitle="Scan, understand, and improve your website's technical health."
        right={lastLabel}
      />

      {/* URL / scan bar */}
      <div className="card" style={{ marginBottom: 18 }}>
        <div className="flex items-center gap-3" style={{ flexWrap: "wrap" }}>
          <input
            className="input"
            style={{ flex: "1 1 320px" }}
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com"
            onKeyDown={(e) => e.key === "Enter" && onScan()}
          />
          <button className="btn primary" onClick={onScan} disabled={status === "running"}>
            {status === "running" ? "Scanning…" : <><RadarIcon size={15} /> Run Health Scan</>}
          </button>
          <Link className="btn" to="/history">Compare with Previous Scan</Link>
        </div>
        <div className="dim mt-2" style={{ fontSize: ".8rem" }}>
          Polite crawling enabled — SitePulse scans responsibly.
        </div>
      </div>

      {status === "running" && <ScanProgress />}
      {status === "error" && (
        <div className="card" style={{ borderColor: "rgba(248,113,113,0.4)" }}>
          <b style={{ color: "var(--red)" }}>Scan failed.</b>
          <div className="muted mt-2">{error}</div>
          <div className="dim mt-2" style={{ fontSize: ".82rem" }}>
            Check the URL is reachable and the API is running, then try again.
          </div>
        </div>
      )}

      {!scan && status !== "running" && status !== "error" && <EmptyState />}

      {scan && status !== "running" && <Results scan={scan} prev={prev} />}
    </>
  );
}

/* --- Results --------------------------------------------------------- */

function Results({ scan, prev }) {
  const st = scoreStatus(scan.score ?? 0);
  const m = scan.metrics || {};
  return (
    <>
      {/* Score + summary */}
      <div className="grid cols-2" style={{ gridTemplateColumns: "320px 1fr", marginBottom: 18 }}>
        <div className="card hover" style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
          <div className="muted" style={{ alignSelf: "flex-start", fontWeight: 600 }}>
            Website Health Score
          </div>
          <div style={{ margin: "10px 0 4px" }}>
            <ScoreGauge score={scan.score ?? 0} grade={scan.grade} size={200} />
          </div>
        </div>

        <div className="card">
          <div className="flex items-center gap-2" style={{ fontWeight: 700 }}>
            <span style={{ color: "var(--cyan)", display: "inline-flex" }}><SparkleIcon size={16} /></span>
            Summary
          </div>
          <p className="muted" style={{ lineHeight: 1.6, marginTop: 8 }}>
            SitePulse scanned <b style={{ color: "var(--text)" }}>{scan.rootUrl}</b> and
            found <b style={{ color: "var(--text)" }}>{m.issuesFound}</b> issue
            {m.issuesFound === 1 ? "" : "s"} across{" "}
            <b style={{ color: "var(--text)" }}>{m.pagesScanned}</b> page
            {m.pagesScanned === 1 ? "" : "s"}. The overall health is{" "}
            <b className={st.cls}>{st.label.toLowerCase()}</b>
            {m.highCount > 0 && (
              <> — the most urgent items are the <b style={{ color: "var(--red)" }}>{m.highCount} high-severity</b> issue{m.highCount === 1 ? "" : "s"}</>
            )}
            .
          </p>
          <span className="trust mt-3">
            Detected by <b>SitePulse Analyzer</b> · Explained by AI
          </span>
        </div>
      </div>

      {/* Metric cards (with trend vs previous scan) */}
      <div className="grid cols-5" style={{ marginBottom: 8 }}>
        <Metric label="Pages scanned" value={m.pagesScanned} icon={<DocIcon size={16} />} />
        <Metric label="Issues found" value={m.issuesFound} icon={<WarningIcon size={16} />}
          delta={trend(m.issuesFound, prev?.issuesCount)} lowerIsBetter />
        <Metric label="Broken links" value={m.brokenLinks} icon={<LinkIcon size={16} />} />
        <Metric label="Avg response" value={fmtTime(m.averageResponseTime)} icon={<ClockIcon size={16} />} />
        <Metric label="Critical issues" value={m.highCount} icon={<DotAlertIcon size={16} />} accent="var(--red)"
          delta={trend(m.highCount, prev?.highCount)} lowerIsBetter />
      </div>

      {/* Health by category */}
      <div className="section-title">Health by Category</div>
      <div className="grid cols-4">
        {(scan.categoryScores || []).map((c) => (
          <CategoryCard key={c.category} category={c.category} score={c.score} issues={scan.issues} />
        ))}
        {(scan.categoryScores || []).length === 0 && (
          <div className="muted">No category scores available.</div>
        )}
      </div>

      {/* Recommended Action Plan */}
      <ActionPlan scan={scan} />
    </>
  );
}

function Metric({ label, value, icon, accent, delta, lowerIsBetter }) {
  // delta = numeric change vs previous scan (or null).
  let deltaEl = null;
  if (delta != null && delta !== 0) {
    const good = lowerIsBetter ? delta < 0 : delta > 0;
    deltaEl = (
      <div style={{ fontSize: ".76rem", marginTop: 2, color: good ? "var(--green)" : "var(--red)" }}>
        {delta > 0 ? "▲ +" : "▼ "}{delta} since last scan
      </div>
    );
  }
  return (
    <div className="card hover" style={{ padding: "16px 18px" }}>
      <div className="dim flex items-center gap-2" style={{ fontSize: ".78rem" }}>{icon} {label}</div>
      <div style={{ fontSize: "1.7rem", fontWeight: 800, marginTop: 6, color: accent || "var(--text)" }}>
        {value ?? "—"}
      </div>
      {deltaEl}
    </div>
  );
}

function CategoryCard({ category, score, issues }) {
  const meta = categoryMeta(category);
  const st = scoreStatus(score);
  const count = (issues || []).filter((i) => i.category === category).length;
  return (
    <div className="card hover">
      <div className="flex items-center gap-2" style={{ fontWeight: 700 }}>
        <span style={{ color: "var(--cyan)", display: "inline-flex" }}>
          <CategoryIcon name={category} size={18} />
        </span>
        <span>{meta.label}</span>
      </div>
      <div style={{ fontSize: "1.5rem", fontWeight: 800, marginTop: 8 }}>
        {score}
        <span className="dim" style={{ fontSize: ".9rem", fontWeight: 600 }}> / 100</span>
      </div>
      <div className="bar mt-2">
        <span style={{ width: `${score}%`, background: st.color }} />
      </div>
      <div className="flex items-center justify-between mt-2" style={{ fontSize: ".8rem" }}>
        <span className={st.cls} style={{ fontWeight: 600 }}>{st.label}</span>
        <span className="muted">{count} issue{count === 1 ? "" : "s"}</span>
      </div>
      {count > 0 && (
        <Link
          to={`/issues?category=${encodeURIComponent(category)}`}
          style={{ color: "var(--cyan)", fontSize: ".8rem", fontWeight: 600, display: "inline-block", marginTop: 8 }}
        >
          <span className="flex items-center gap-2">View issues <ArrowRightIcon size={13} /></span>
        </Link>
      )}
    </div>
  );
}

/* --- Recommended Action Plan ----------------------------------------- */

const SEV_RANK = { High: 0, Medium: 1, Low: 2 };
const IMPACT = { High: "High impact", Medium: "Moderate impact", Low: "Low impact" };

function ActionPlan({ scan }) {
  const issues = scan.issues || [];
  if (issues.length === 0) {
    return (
      <>
        <div className="section-title">Recommended Action Plan</div>
        <div className="card muted flex items-center gap-2"><span style={{ color: "var(--cyan)", display: "inline-flex" }}><CelebrateIcon size={16} /></span> No issues found — nothing to fix.</div>
      </>
    );
  }

  // Group by issue type, keep the worst severity + page count, order by severity.
  // issues are deduped rows; affectedPages tells us how many pages each covers.
  const groups = {};
  for (const i of issues) {
    const g = (groups[i.issueType] ??= { type: i.issueType, severity: i.severity, count: 0, sample: i });
    g.count += i.affectedPages || 1;
    if (SEV_RANK[i.severity] < SEV_RANK[g.severity]) { g.severity = i.severity; g.sample = i; }
  }
  const plan = Object.values(groups)
    .sort((a, b) => SEV_RANK[a.severity] - SEV_RANK[b.severity] || b.count - a.count)
    .slice(0, 6);

  return (
    <>
      <div className="section-title">Recommended Action Plan</div>
      <div className="card">
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {plan.map((g, idx) => {
            const h = humanize(g.sample);
            return (
              <div key={g.type} className="action-row">
                <div className="num">{idx + 1}</div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 700 }}>
                    {actionVerb(g.type)} {g.count > 1 ? `(${g.count} pages)` : ""}
                  </div>
                  <div className="meta muted mt-2">
                    <span>Priority: <b className={"status-" + (g.severity === "High" ? "critical" : g.severity === "Medium" ? "needs" : "good")}>{g.severity}</b></span>
                    <span>Effort: <b>{h.effort}</b></span>
                    <span>{IMPACT[g.severity]}</span>
                  </div>
                </div>
                <Link className="btn" to={`/issues?category=${encodeURIComponent(g.sample.category)}`}>
                  Start Fix <ArrowRightIcon size={13} />
                </Link>
              </div>
            );
          })}
        </div>
        <div className="dim mt-3" style={{ fontSize: ".8rem", marginTop: 12 }}>
          Tackle the highest-priority items first, then re-run the scan to see your score improve.
        </div>
      </div>
    </>
  );
}

function actionVerb(type) {
  // Turn an issue type into an imperative action.
  const map = {
    "Missing Title": "Add page titles",
    "Missing Meta Description": "Add meta descriptions",
    "Missing H1": "Add main headings",
    "Image Missing Alt": "Add image alt text",
    "Broken Link": "Fix broken links",
    "Slow Response Time": "Improve response time",
    "Site Not Served Over HTTPS": "Switch the site to HTTPS",
    "Missing Structured Data": "Add structured data",
  };
  return map[type] || `Fix: ${type}`;
}

/* --- Scan-in-progress ------------------------------------------------ */

function ScanProgress() {
  return (
    <div className="card">
      <div className="flex items-center gap-2" style={{ fontWeight: 700 }}>
        <span className="pulse-dot" /> Scanning…
      </div>
      <div style={{ margin: "14px 0 2px" }}>
        <PulseLine height={48} beats={5} />
      </div>
      <div className="mt-3" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {SCAN_STEPS.map((s, i) => (
          <div key={i} className="muted flex items-center gap-2" style={{ fontSize: ".9rem" }}>
            <span className="pulse-dot" style={{ animationDelay: `${i * 0.15}s` }} />
            {s}
          </div>
        ))}
      </div>
      <div className="dim mt-3" style={{ fontSize: ".8rem" }}>
        This can take a moment on larger sites — SitePulse crawls politely.
      </div>
    </div>
  );
}

/* --- Empty state ----------------------------------------------------- */

function EmptyState() {
  return (
    <>
      <div className="card" style={{ textAlign: "center", padding: "44px 28px" }}>
        <HeroLockup />
        <div style={{ fontSize: "1.3rem", fontWeight: 700, marginTop: 28 }}>
          Start your first website health scan
        </div>
        <div className="muted" style={{ maxWidth: 600, margin: "8px auto 0", lineHeight: 1.6 }}>
          Enter a URL above and SitePulse will crawl your website, detect technical
          issues, explain them in plain language, and suggest practical fixes.
        </div>
      </div>
      <div className="grid cols-3" style={{ marginTop: 18 }}>
        <Feature icon={<RadarIcon size={18} />} title="Detect hidden issues"
          text="Crawls your pages and runs deterministic health, SEO, security and accessibility checks." />
        <Feature icon={<BulbIcon size={18} />} title="Understand what matters"
          text="Every issue is scored by severity and explained in simple, non-technical language." />
        <Feature icon={<RobotIcon size={18} />} title="Fix with AI guidance"
          text="Get ready-to-paste fixes and track your site's health over time." />
      </div>
    </>
  );
}

function Feature({ icon, title, text }) {
  return (
    <div className="card hover">
      <div className="flex items-center gap-2" style={{ fontWeight: 700 }}>
        <span style={{ color: "var(--cyan)", display: "inline-flex" }}>{icon}</span> {title}
      </div>
      <div className="muted mt-2" style={{ lineHeight: 1.55 }}>{text}</div>
    </div>
  );
}

/* --- helpers --------------------------------------------------------- */

// Numeric change of a metric vs its previous value (null if no previous).
function trend(current, previous) {
  if (previous == null || current == null) return null;
  return current - previous;
}
function fmtTime(t) {
  if (t == null) return "—";
  return `${t.toFixed(2)}s`;
}
function timeAgo(d) {
  const s = Math.floor((Date.now() - d.getTime()) / 1000);
  if (s < 60) return "just now";
  const m = Math.floor(s / 60);
  if (m < 60) return `${m} minute${m === 1 ? "" : "s"} ago`;
  const h = Math.floor(m / 60);
  return `${h} hour${h === 1 ? "" : "s"} ago`;
}
