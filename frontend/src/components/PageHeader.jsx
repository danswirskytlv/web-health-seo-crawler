// Top-of-page title + subtitle + optional right-aligned meta/actions.
export default function PageHeader({ title, subtitle, right }) {
  return (
    <div className="topbar">
      <div>
        <div className="page-title">{title}</div>
        {subtitle && <div className="page-sub">{subtitle}</div>}
      </div>
      {right && <div className="top-meta">{right}</div>}
    </div>
  );
}
