import { Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar.jsx";
import Placeholder from "./screens/Placeholder.jsx";
import Overview from "./screens/Overview.jsx";
import Scan from "./screens/Scan.jsx";
import Issues from "./screens/Issues.jsx";
import Chat from "./screens/Chat.jsx";
import Reports from "./screens/Reports.jsx";
import History from "./screens/History.jsx";
import Settings from "./screens/Settings.jsx";

export default function App() {
  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main">
        <div className="content-max">
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/scan" element={<Scan />} />
            <Route path="/issues" element={<Issues />} />
            <Route path="/ai" element={<Chat />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/history" element={<History />} />
            <Route path="/settings" element={<Settings />} />
            <Route
              path="*"
              element={<Placeholder title="Not found" subtitle="That page doesn't exist." />}
            />
          </Routes>

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
