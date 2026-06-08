// Shared scan state, so every screen (Overview, Issues, AI, …) sees the same
// current scan and can trigger a new one.

import { createContext, useContext, useState, useCallback } from "react";
import { api } from "../api.js";

const ScanContext = createContext(null);

export function ScanProvider({ children }) {
  const [scan, setScan] = useState(null);       // last scan result (JSON)
  const [status, setStatus] = useState("idle"); // idle | running | done | error
  const [error, setError] = useState(null);
  const [lastScanAt, setLastScanAt] = useState(null);

  const runScan = useCallback(async (opts) => {
    setStatus("running");
    setError(null);
    try {
      const result = await api.scan(opts);
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

  const clearScan = useCallback(() => {
    setScan(null);
    setStatus("idle");
    setError(null);
  }, []);

  return (
    <ScanContext.Provider
      value={{ scan, status, error, lastScanAt, runScan, clearScan }}
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
