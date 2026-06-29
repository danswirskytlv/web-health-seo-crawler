// Shared scan state, so every screen (Overview, Issues, AI, …) sees the same
// current scan and can trigger a new one. Also caches AI fix explanations
// per-issue so reopening the drawer doesn't re-call Gemini.

import { createContext, useContext, useState, useCallback, useRef } from "react";
import { api } from "../api.js";

const ScanContext = createContext(null);

// A stable identity for an issue (the same issue across renders).
function issueKey(issue) {
  return `${issue.url}::${issue.issueType}`;
}

export function ScanProvider({ children }) {
  const [scan, setScan] = useState(null);       // last scan result (JSON)
  const [status, setStatus] = useState("idle"); // idle | running | done | error
  const [error, setError] = useState(null);
  const [lastScanAt, setLastScanAt] = useState(null);

  // Per-issue AI-fix cache for the CURRENT scan. Cleared on a new scan.
  const aiFixCache = useRef(new Map());

  const runScan = useCallback(async (opts) => {
    setStatus("running");
    setError(null);
    try {
      const result = await api.scan(opts);
      aiFixCache.current = new Map(); // fresh scan -> fresh AI cache
      setScan(result);
      setStatus("done");
      setLastScanAt(new Date());
      return result;
    } catch (e) {
      setError(e.message || "Scan failed");
      setStatus("error");
      throw e;
    }
  }, []);

  // Return the AI fix for an issue — from cache if we already have a GOOD
  // (Gemini) result, otherwise fetch it. We deliberately do NOT cache
  // fallback responses, so a transient AI outage can be retried later instead
  // of being stuck showing the fallback forever. `force` re-fetches always.
  const getAiFix = useCallback(async (issue, force = false) => {
    const key = issueKey(issue);
    if (!force && aiFixCache.current.has(key)) {
      return aiFixCache.current.get(key);
    }
    const result = await api.aiFix(issue);
    if (result && result.source === "gemini") {
      aiFixCache.current.set(key, result);  // cache only real AI answers
    }
    return result;
  }, []);

  const clearScan = useCallback(() => {
    setScan(null);
    setStatus("idle");
    setError(null);
    aiFixCache.current = new Map();
  }, []);

  return (
    <ScanContext.Provider
      value={{ scan, status, error, lastScanAt, runScan, clearScan, getAiFix }}
    >
      {children}
    </ScanContext.Provider>
  );
}

export function useScan() {
  const ctx = useContext(ScanContext);
  if (!ctx) throw new Error("useScan must be used inside <ScanProvider>");
  return ctx;
}
