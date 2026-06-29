import { NavLink, Link } from "react-router-dom";
import Logo, { Wordmark } from "./Logo.jsx";
import PulseLine from "./PulseLine.jsx";
import {
  OverviewIcon,
  ScanIcon,
  IssuesIcon,
  AiIcon,
  ReportsIcon,
  HistoryIcon,
  SettingsIcon,
} from "./NavIcons.jsx";

const NAV = [
  { to: "/app", label: "Overview", Icon: OverviewIcon, end: true },
  { to: "/scan", label: "Scan", Icon: ScanIcon },
  { to: "/issues", label: "Issues", Icon: IssuesIcon },
  { to: "/ai", label: "AI Fix Assistant", Icon: AiIcon },
  { to: "/reports", label: "Reports", Icon: ReportsIcon },
  { to: "/history", label: "History", Icon: HistoryIcon },
  { to: "/settings", label: "Settings", Icon: SettingsIcon },
];

export default function Sidebar() {
  return (
    <aside className="rail">
      <Link to="/app" className="brand" aria-label="SitePulse home">
        <Logo size={26} />
        <Wordmark />
      </Link>
      <div className="brand-sub">AI Website Health Assistant</div>

      <div style={{ padding: "2px 8px 10px" }}>
        <PulseLine height={26} beats={3} />
      </div>

      <div className="nav-group-label">Navigation</div>
      {NAV.map((item) => {
        const Icon = item.Icon;
        return (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) => "nav-item" + (isActive ? " active" : "")}
          >
            <span className="ico"><Icon size={18} /></span>
            <span>{item.label}</span>
          </NavLink>
        );
      })}

      <div className="rail-footer">
        Polite · Deterministic · Transparent · AI-Powered.
      </div>
    </aside>
  );
}
