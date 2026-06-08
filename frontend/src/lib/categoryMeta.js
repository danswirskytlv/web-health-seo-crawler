// Display metadata per audit category — mirrors the backend's categories.
export const CATEGORY_META = {
  SEO: { icon: "🔍", label: "SEO" },
  Accessibility: { icon: "♿", label: "Accessibility" },
  Performance: { icon: "⚡", label: "Performance" },
  Schema: { icon: "📐", label: "Schema" },
  "Transport Security": { icon: "🔐", label: "Transport Security" },
  "Security Headers": { icon: "🛡️", label: "Security Headers" },
  Cookies: { icon: "🍪", label: "Cookies" },
  "Information Disclosure": { icon: "📢", label: "Information Disclosure" },
  Privacy: { icon: "🕵️", label: "Privacy" },
  Security: { icon: "🔒", label: "Security" }, // legacy
};

export function categoryMeta(name) {
  return CATEGORY_META[name] || { icon: "•", label: name };
}

// Status label + CSS color class for a 0-100 score.
export function scoreStatus(score) {
  if (score >= 90) return { label: "Excellent", cls: "status-excellent", color: "var(--green)" };
  if (score >= 75) return { label: "Good", cls: "status-good", color: "var(--green)" };
  if (score >= 50) return { label: "Needs Improvement", cls: "status-needs", color: "var(--amber)" };
  return { label: "Critical", cls: "status-critical", color: "var(--red)" };
}

// Severity -> badge class.
export function severityClass(sev) {
  return sev === "High" ? "high" : sev === "Medium" ? "medium" : "low";
}
