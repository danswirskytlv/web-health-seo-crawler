// SitePulse API client.
// During dev, Vite proxies "/api" -> http://localhost:8001 (see vite.config.js),
// so we can use relative URLs here.

const BASE = "/api";

async function request(path, options = {}) {
  const res = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* ignore non-JSON error bodies */
    }
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  health: () => request("/health"),

  // Run a scan. opts: { url, maxPages, maxDepth, checkTls, checkExposedPaths, save }
  scan: (opts) =>
    request("/scan", { method: "POST", body: JSON.stringify(opts) }),

  // History
  listScans: (rootUrl, limit = 50) => {
    const qs = new URLSearchParams();
    if (rootUrl) qs.set("rootUrl", rootUrl);
    qs.set("limit", String(limit));
    return request("/scans?" + qs.toString());
  },
  getScan: (id) => request("/scans/" + id),
  diff: (fromId, toId) =>
    request(`/diff?fromId=${fromId}&toId=${toId}`),

  // Report download URLs (used directly as href / window.open targets).
  reportUrl: (scanId, kind) => `${BASE}/scans/${scanId}/report/${kind}`,

  // AI
  aiFix: (issue) =>
    request("/ai/fix", { method: "POST", body: JSON.stringify({ issue }) }),
  aiRootCause: (fromId, toId) =>
    request(`/ai/root-cause?fromId=${fromId}&toId=${toId}`, { method: "POST" }),
  aiChat: (message, history, scanId) =>
    request("/ai/chat", {
      method: "POST",
      body: JSON.stringify({ message, history, scanId }),
    }),
};
