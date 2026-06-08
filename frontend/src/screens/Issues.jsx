import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import PageHeader from "../components/PageHeader.jsx";
import AiFixDrawer from "../components/AiFixDrawer.jsx";
import { useScan } from "../state/ScanContext.jsx";
import { categoryMeta, severityClass } from "../lib/categoryMeta.js";
import { humanize } from "../lib/humanize.js";

const SEVERITY_ORDER = { High: 0, Medium: 1, Low: 2 };

export default function Issues() {
  const { scan } = useScan();
  const [params] = useSearchParams();
  const [query, setQuery] = useState("");
  const [sevFilter, setSevFilter] = useState("All");
  const [catFilter, setCatFilter] = useState(params.get("category") || "All");
  const [sort, setSort] = useState("severity");
  const [selected, setSelected] = useState(null);

  const issues = scan?.issues || [];

  const categories = useMemo(
    () => ["All", ...Array.from(new Set(issues.map((i) => i.category))).sort()],
    [issues]
  );

  const filtered = useMemo(() => {
    let list = issues.filter((i) => {
      if (sevFilter !== "All" && i.severity !== sevFilter) return false;
      if (catFilter !== "All" && i.category !== catFilter) return false;
      if (query) {
        const q = query.toLowerCase();
        const hay = (i.issueType + " " + i.url + " " + i.description + " " + i.category).toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
    list = [...list].sort((a, b) => {
      if (sort === "severity") return SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity];
      if (sort === "page") return a.url.localeCompare(b.url);
      if (sort === "category") return a.category.localeCompare(b.category);
      return 0;
    });
    return list;
  }, [issues, sevFilter, catFilter, query, sort]);

  if (!scan) {
    return (
      <>
        <PageHeader title="Issues" subtitle="Every detected problem, filterable and actionable." />
        <div className="card" style={{ textAlign: "center", padding: "40px 24px" }}>
          <div className="muted">Run a scan from the Overview screen to see detected issues here.</div>
        </div>
      </>
    );
  }

  return (
    <>
      <PageHeader
        title="Issues"
        subtitle={`${issues.length} issue${issues.length === 1 ? "" : "s"} detected on ${scan.rootUrl}`}
      />

      {/* Controls */}
      <div className="card" style={{ marginBottom: 16 }}>
        <input
          className="input"
          placeholder="Search issues by page, category, or description"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <div className="flex items-center gap-2 mt-3" style={{ flexWrap: "wrap" }}>
          {["All", "High", "Medium", "Low"].map((s) => (
            <Chip key={s} active={sevFilter === s} onClick={() => setSevFilter(s)}>
              {s}
            </Chip>
          ))}
          <span style={{ width: 1, height: 20, background: "var(--border)", margin: "0 4px" }} />
          {categories.map((c) => (
            <Chip key={c} active={catFilter === c} onClick={() => setCatFilter(c)}>
              {c === "All" ? "All categories" : `${categoryMeta(c).icon} ${categoryMeta(c).label}`}
            </Chip>
          ))}
          <span style={{ marginLeft: "auto" }} className="dim">Sort:</span>
          <select className="input" style={{ width: "auto" }} value={sort} onChange={(e) => setSort(e.target.value)}>
            <option value="severity">Severity</option>
            <option value="page">Page</option>
            <option value="category">Category</option>
          </select>
        </div>
      </div>

      {/* Issue list */}
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {filtered.map((issue, idx) => (
          <IssueRow key={idx} issue={issue} onSelect={() => setSelected(issue)} />
        ))}
        {filtered.length === 0 && (
          <div className="card muted" style={{ textAlign: "center" }}>
            No issues match your filters.
          </div>
        )}
      </div>

      <AiFixDrawer issue={selected} onClose={() => setSelected(null)} />
    </>
  );
}

function Chip({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className="badge"
      style={{
        cursor: "pointer",
        background: active ? "rgba(34,211,238,0.16)" : "transparent",
        borderColor: active ? "var(--cyan)" : "var(--border)",
        color: active ? "var(--text)" : "var(--text-muted)",
        fontWeight: 600,
      }}
    >
      {children}
    </button>
  );
}

function IssueRow({ issue, onSelect }) {
  const meta = categoryMeta(issue.category);
  const h = humanize(issue);
  return (
    <div className="card hover" style={{ padding: "14px 16px" }}>
      <div className="flex items-center justify-between gap-3" style={{ flexWrap: "wrap" }}>
        <div style={{ minWidth: 0, flex: "1 1 420px" }}>
          <div className="flex items-center gap-2" style={{ flexWrap: "wrap" }}>
            <span className={"badge " + severityClass(issue.severity)}>{issue.severity}</span>
            <span className="badge">{meta.icon} {meta.label}</span>
            <span style={{ fontWeight: 700 }}>{issue.issueType}</span>
          </div>
          <div className="muted mt-2" style={{ fontSize: ".9rem", lineHeight: 1.5 }}>{h.plain}</div>
          <div className="dim mt-2" style={{ fontSize: ".8rem", wordBreak: "break-all" }}>
            {issue.url}
            {issue.statusCode != null && <span> · HTTP {issue.statusCode}</span>}
            <span> · Fix effort: {h.effort}</span>
          </div>
        </div>
        <button className="btn primary" onClick={onSelect}>✨ Explain &amp; Fix</button>
      </div>
    </div>
  );
}
