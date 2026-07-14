import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import Logo from "../components/Logo.jsx";
import PulseLine from "../components/PulseLine.jsx";
import { useScan } from "../state/ScanContext.jsx";
import { ArrowRightIcon } from "../components/Icons.jsx";

// Full-bleed marketing landing page (the app's home at "/"). No sidebar.
// "Begin diagnosis" kicks off a scan and routes into the dashboard at /app.
export default function Landing() {
  const navigate = useNavigate();
  const { runScan } = useScan();
  const [url, setUrl] = useState("");

  const begin = () => {
    const u = url.trim();
    if (!u) {
      navigate("/app");
      return;
    }
    const full = /^https?:\/\//i.test(u) ? u : `https://${u}`;
    // Fire the scan, then jump into the dashboard which shows progress + results.
    runScan({ url: full, checkTls: true, save: true }).catch(() => {});
    navigate("/app");
  };

  return (
    <div className="landing">
      {/* faint dotted backdrop */}
      <div className="landing-grid" aria-hidden="true" />

      {/* Header */}
      <header className="landing-header">
        <Link to="/" className="landing-brand" aria-label="SitePulse home">
          <Logo size={26} />
          <span className="wordmark">
            <span className="site">Site</span>
            <span className="pulse">Pulse</span>
          </span>
        </Link>
        <nav className="landing-nav">
          <a className="landing-nav-link" href="#">Diagnostics</a>
          <a className="landing-nav-link" href="#">Method</a>
          <a className="landing-nav-link" href="#">Pricing</a>
        </nav>
        <div className="landing-actions">
          <a className="landing-nav-link" href="#">Sign in</a>
          <button className="btn console-btn" onClick={() => navigate("/app")}>
            Open console <ArrowRightIcon size={14} />
          </button>
        </div>
      </header>

      {/* Hero */}
      <main className="landing-hero">
        <div className="eyebrow label-mono">● Website Health Intelligence</div>

        <h1 className="hero-headline">
          The <span className="pulse">pulse</span> of<br />your website.
        </h1>

        <p className="hero-sub">
          Scan any site. Read its vitals. SitePulse detects every anomaly and
          prescribes the cure — a full diagnostic work-up in under a minute.
        </p>

        {/* Big live pulse in the center of the screen */}
        <div className="hero-bigpulse" aria-hidden="true">
          <PulseLine height={150} beats={6} />
        </div>

        {/* URL input */}
        <div className="hero-input">
          <span className="hero-input-ico">⌕</span>
          <input
            className="hero-input-field"
            placeholder="https://your-website.com"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && begin()}
          />
          <button className="btn primary hero-begin" onClick={begin}>
            Begin diagnosis <ArrowRightIcon size={15} />
          </button>
        </div>

        <div className="hero-foot label-mono">
          No account needed · Read-only crawl · ~60s
        </div>
      </main>

      {/* Footer strip */}
      <footer className="landing-footer label-mono">
        <span>+ Recently diagnosed</span>
        <span className="dim">2.4M pages scanned</span>
      </footer>
    </div>
  );
}
