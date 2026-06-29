import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import PageHeader from "../components/PageHeader.jsx";
import AiFixDrawer from "../components/AiFixDrawer.jsx";
import { useScan } from "../state/ScanContext.jsx";
import { categoryMeta, severityClass } from "../lib/categoryMeta.js";
import { humanize } from "../lib/humanize.js";
import { CategoryIcon, SparkleIcon, NoteIcon } from "../components/Icons.jsx";

const SEVERITY_ORDER = { High: 0, Medium: 1, Low: 2 };

export default function Issues() {
  const { scan } = useScan();
  const [params] = useSearchParams();
  const [query, setQuery] = useState("");
  const [sevFilter, setSevFilter] = useState("All");
  const [catFilter, setCatFilter] = useState(params.get("category") || "All");
  const [sort, setSort] = useState("severity");
  const [selected, setSelected] = useState(null);

  const allIssues = scan?.issues || [];

  // Informational notes (e.g. the grouped 404 list) are shown in their own
  // section at the bottom, NOT mixed into the bug list — they're heads-ups,
  // not confirmed defects.
  const isNote = (i) => i.issueType === "Pages Returning 404" || !!i.details?.urls;
  const notes = useMemo(() => allIssues.filter(isNote), [allIssues]);
  const issues = useMemo(() => allIssues.filter((i) => !isNote(i)), [allIssues]);

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
              {c === "All" ? (
                "All categories"
              ) : (
                <span className="flex items-center gap-2">
                  <CategoryIcon name={c} size={14} />
                  {categoryMeta(c).label}
                </span>
              )}
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
          <IssueRow
            key={`${issue.url}::${issue.issueType}::${idx}`}
            issue={issue}
            onSelect={() => setSelected(issue)}
          />
        ))}
        {filtered.length === 0 && (
          <div className="card muted" style={{ textAlign: "center" }}>
            No issues match your filters.
          </div>
        )}
      </div>

      {/* Notes — informational, not bugs. Shown only when there are some. */}
      {notes.length > 0 && (
        <div style={{ marginTop: 28 }}>
          <div
            className="flex items-center gap-2"
            style={{ marginBottom: 12, fontWeight: 700, fontSize: "1.05rem" }}
          >
            <span className="flex items-center gap-2"><NoteIcon size={16} /> Notes</span>
            <span className="badge">{notes.length}</span>
          </div>
          <div className="muted" style={{ fontSize: ".85rem", marginBottom: 12 }}>
            Things worth a manual look — not confirmed problems.
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {notes.map((note, idx) => (
              <NoteCard key={`note::${idx}`} note={note} onSelect={() => setSelected(note)} />
            ))}
          </div>
        </div>
      )}

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

function NoteCard({ note, onSelect }) {
  const urls = note.details?.urls || [];
  return (
    <div className="card" style={{ padding: "16px 18px", borderColor: "var(--border)" }}>
      <div className="flex items-center justify-between gap-3" style={{ flexWrap: "wrap" }}>
        <div className="flex items-center gap-2" style={{ flexWrap: "wrap" }}>
          <span className="badge"><NoteIcon size={13} /> Note</span>
          <span style={{ fontWeight: 700 }}>{note.issueType}</span>
          {urls.length > 0 && (
            <span className="badge">{urls.length} URL{urls.length === 1 ? "" : "s"}</span>
          )}
        </div>
        <button className="btn primary" onClick={onSelect}><SparkleIcon size={15} /> Explain &amp; Fix</button>
      </div>

      <div className="muted mt-2" style={{ fontSize: ".9rem", lineHeight: 1.55 }}>
        These URLs returned “page not found” (HTTP 404) during the scan. A 404 can
        mean the page is genuinely missing, or that the site is blocking our
        scanner (common with Shopify, Cloudflare and similar) and the page works
        fine in a real browser. We can’t tell which from the outside — it’s worth
        opening each one in a browser to check.
      </div>

      {urls.length > 0 && (
        <ul
          style={{
            margin: "14px 0 0",
            padding: "12px 14px",
            listStyle: "none",
            background: "rgba(255,255,255,0.03)",
            border: "1px solid var(--border)",
            borderRadius: 10,
            display: "flex",
            flexDirection: "column",
            gap: 6,
          }}
        >
          {urls.map((u) => (
            <li key={u} style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ color: "var(--red)", fontSize: ".75rem" }}>404</span>
              <a
                href={u}
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: "var(--cyan)", wordBreak: "break-all", fontSize: ".85rem" }}
              >
                {u}
              </a>
            </li>
          ))}
        </ul>
      )}
    </div>
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
            <span className="badge"><CategoryIcon name={issue.category} size={13} /> {meta.label}</span>
            <span style={{ fontWeight: 700 }}>{issue.issueType}</span>
          </div>
          <div className="muted mt-2" style={{ fontSize: ".9rem", lineHeight: 1.5 }}>{h.plain}</div>
          <div className="dim mt-2" style={{ fontSize: ".8rem", wordBreak: "break-all" }}>
            {issue.url}
            {/* Only show the status code when it's actually a problem (4xx/5xx).
                A 200 is healthy and would just read as a false alarm. */}
            {issue.statusCode != null && issue.statusCode >= 400 && (
              <span style={{ color: "var(--red)" }}> · HTTP {issue.statusCode}</span>
            )}
            <span> · Fix effort: {h.effort}</span>
            {issue.groupedCount > 1 && (
              <span style={{ color: "var(--amber)" }}> · {issue.groupedCount} on this page</span>
            )}
            {issue.affectedPages > 1 && (
              <span style={{ color: "var(--amber)" }}> · affects {issue.affectedPages} pages</span>
            )}
          </div>
        </div>
        <button className="btn primary" onClick={onSelect}><SparkleIcon size={15} /> Explain &amp; Fix</button>
      </div>
    </div>
  );
}
