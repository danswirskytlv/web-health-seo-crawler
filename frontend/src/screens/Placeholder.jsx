import PageHeader from "../components/PageHeader.jsx";

// A temporary screen used until each real screen is built (Phase C+).
export default function Placeholder({ title, subtitle, note }) {
  return (
    <>
      <PageHeader title={title} subtitle={subtitle} />
      <div className="card" style={{ textAlign: "center", padding: "48px 24px" }}>
        <div className="pulse-dot" style={{ margin: "0 auto 14px" }} />
        <div style={{ fontWeight: 700, fontSize: "1.05rem" }}>{title} — coming up</div>
        <div className="muted mt-2" style={{ maxWidth: 520, margin: "8px auto 0" }}>
          {note || "This screen is part of the SitePulse build and will be wired to the live API."}
        </div>
      </div>
    </>
  );
}
