import { NavLink } from "react-router-dom";
import Logo, { Wordmark } from "./Logo.jsx";

const NAV = [
  { to: "/", label: "Overview", icon: "📊", end: true },
  { to: "/scan", label: "Scan", icon: "📡" },
  { to: "/issues", label: "Issues", icon: "⚠️" },
  { to: "/ai", label: "AI Fix Assistant", icon: "🤖" },
  { to: "/reports", label: "Reports", icon: "📄" },
  { to: "/history", label: "History", icon: "📜" },
  { to: "/settings", label: "Settings", icon: "⚙️" },
];

export default function Sidebar() {
  return (
    <aside className="rail">
      <div className="brand">
        <Logo size={26} />
        <Wordmark />
      </div>
      <div className="brand-sub">AI Website Health Assistant</div>

      <div className="nav-group-label">Navigation</div>
      {NAV.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          className={({ isActive }) => "nav-item" + (isActive ? " active" : "")}
        >
          <span className="ico">{item.icon}</span>
          <span>{item.label}</span>
        </NavLink>
      ))}

      <div className="rail-footer">
        Polite · Deterministic · Transparent · AI-Powered.
      </div>
    </aside>
  );
}
