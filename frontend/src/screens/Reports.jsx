import PageHeader from "../components/PageHeader.jsx";
import { useScan } from "../state/ScanContext.jsx";
import { api } from "../api.js";

const REPORTS = [
  {
    kind: "issues.csv",
    icon: "📊",
    title: "Issues CSV",
    desc: "Every detected issue with severity, category, page and description.",
    type: "CSV",
  },
  {
    kind: "pages.csv",
    icon: "📄",
    title: "Pages CSV",
    desc: "Every page scanned, with status code and response time.",
    type: "CSV",
  },
  {
    kind: "report.pdf",
    icon: "📕",
    title: "PDF Health Report",
    desc: "A polished report with the health score, issues and fixes — ready to send to a client or lecturer.",
    type: "PDF",
  },
];

export default function Reports() {
  const { scan } = useScan();

  if (!scan || scan.scanId == null) {
    return (
      <>
        <PageHeader title="Reports" subtitle="Export your results as professional reports." />
        <div className="card" style={{ textAlign: "center", padding: "40px 24px" }}>
          <div className="muted">
            Run a scan from the Overview screen first — then you can export it here.
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <PageHeader
        title="Reports"
        subtitle={`Export the latest scan of ${scan.rootUrl}.`}
      />

      <div className="grid cols-3">
        {REPORTS.map((r) => (
          <div key={r.kind} className="card hover">
            <div style={{ fontSize: "1.6rem" }}>{r.icon}</div>
            <div style={{ fontWeight: 700, marginTop: 6 }}>{r.title}</div>
            <div className="muted mt-2" style={{ lineHeight: 1.5, minHeight: 48 }}>{r.desc}</div>
            <div className="flex items-center justify-between mt-3">
              <span className="badge">{r.type}</span>
              <a className="btn primary" href={api.reportUrl(scan.scanId, r.kind)}>
                ⬇ Download
              </a>
            </div>
          </div>
        ))}
      </div>

      <div className="card mt-3" style={{ marginTop: 18 }}>
        <div style={{ fontWeight: 700 }}>Your report includes</div>
        <div className="muted mt-2" style={{ lineHeight: 1.7 }}>
          Health score and grade · detected issues by severity · affected pages ·
          plain-language explanations · suggested fixes.
        </div>
      </div>
    </>
  );
}
