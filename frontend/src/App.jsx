import { Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar.jsx";
import Placeholder from "./screens/Placeholder.jsx";
import Landing from "./screens/Landing.jsx";
import Overview from "./screens/Overview.jsx";
import Scan from "./screens/Scan.jsx";
import Issues from "./screens/Issues.jsx";
import Chat from "./screens/Chat.jsx";
import Reports from "./screens/Reports.jsx";
import History from "./screens/History.jsx";
import Settings from "./screens/Settings.jsx";

// The dashboard application shell (sidebar + main content). Used for every
// route except the full-bleed landing page.
function DashboardShell({ children }) {
  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main">
        <div className="content-max">
          {children}
          <footer className="app-footer">
            <span className="tag">
              Your website health, monitored, explained, and improved over time.
            </span>
            <span className="mono">Polite. Deterministic. Transparent. AI-Powered.</span>
          </footer>
        </div>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      {/* Full-bleed marketing landing — no sidebar. */}
      <Route path="/" element={<Landing />} />

      {/* Dashboard app (sidebar shell). */}
      <Route path="/app" element={<DashboardShell><Overview /></DashboardShell>} />
      <Route path="/scan" element={<DashboardShell><Scan /></DashboardShell>} />
      <Route path="/issues" element={<DashboardShell><Issues /></DashboardShell>} />
      <Route path="/ai" element={<DashboardShell><Chat /></DashboardShell>} />
      <Route path="/reports" element={<DashboardShell><Reports /></DashboardShell>} />
      <Route path="/history" element={<DashboardShell><History /></DashboardShell>} />
      <Route path="/settings" element={<DashboardShell><Settings /></DashboardShell>} />
      <Route
        path="*"
        element={
          <DashboardShell>
            <Placeholder title="Not found" subtitle="That page doesn't exist." />
          </DashboardShell>
        }
      />
    </Routes>
  );
}
