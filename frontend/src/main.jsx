import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App.jsx";
import { ScanProvider } from "./state/ScanContext.jsx";
import "./styles/theme.css";

/* Runtime accent default — the "CSS alone won't win" fix. A tweaks/theme layer
   can set an inline custom property on <html> that beats the stylesheet :root
   rule by specificity, so we write our default --signal (and derived tints)
   onto documentElement at startup. Call applyAccent(hex) to change it. */
export const DEFAULT_SIGNAL = "#34d2f2";
export function applyAccent(hex = DEFAULT_SIGNAL) {
  const el = document.documentElement;
  const mix = (pct) => `color-mix(in srgb, ${hex} ${pct}%, transparent)`;
  el.style.setProperty("--signal", hex);
  el.style.setProperty("--signal-glow", mix(35));
  el.style.setProperty("--signal-soft", mix(14));
  el.style.setProperty("--signal-faint", mix(6));
  el.style.setProperty("--cyan", hex);
  el.style.setProperty("--cyan-glow", mix(35));
}
applyAccent();

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <ScanProvider>
        <App />
      </ScanProvider>
    </BrowserRouter>
  </React.StrictMode>
);
