// Plain-language phrasing for issue types — turns technical names into
// something a non-technical site owner understands, plus a rough fix-effort
// hint. Falls back to the issue's own description when we don't have a mapping.

const FRIENDLY = {
  "Missing Title": {
    plain: "This page has no title for search results and browser tabs.",
    effort: "Easy",
  },
  "Missing Meta Description": {
    plain: "This page is missing the short description shown under its title in search results.",
    effort: "Easy",
  },
  "Missing H1": {
    plain: "This page has no main heading, so its topic is unclear.",
    effort: "Easy",
  },
  "Image Missing Alt": {
    plain: "This image has no description for screen readers and search engines.",
    effort: "Easy",
  },
  "Broken Link": {
    plain: "This link leads to a missing page.",
    effort: "Easy",
  },
  "Pages Returning 404": {
    plain: "Some URLs returned 'page not found'. They may be genuinely missing, or the site may be blocking our scanner — worth checking each one in a browser.",
    effort: "Easy",
  },
  "Server Error": {
    plain: "The server returned an error while loading this page.",
    effort: "Medium",
  },
  "Unreachable Page": {
    plain: "This page couldn't be reached at all.",
    effort: "Medium",
  },
  "Slow Response Time": {
    plain: "This page is slow to respond, which frustrates visitors.",
    effort: "Medium",
  },
  "Site Not Served Over HTTPS": {
    plain: "This site isn't secured with HTTPS, so browsers mark it 'not secure'.",
    effort: "Medium",
  },
  "Mixed Content": {
    plain: "A secure page loads some resources insecurely, weakening its protection.",
    effort: "Medium",
  },
  "Missing HSTS Header": {
    plain: "The site doesn't tell browsers to always use a secure connection.",
    effort: "Easy",
  },
  "target=_blank Without rel=noopener": {
    plain: "Links that open new tabs aren't protected against a known browser trick.",
    effort: "Easy",
  },
  "TLS Certificate Expired": {
    plain: "The security certificate has expired — visitors will see a warning.",
    effort: "Medium",
  },
  "Invalid JSON-LD Syntax": {
    plain: "The structured-data code on this page is broken and search engines ignore it.",
    effort: "Medium",
  },
  "Missing Structured Data": {
    plain: "This page has no structured data, so it can't earn rich search results.",
    effort: "Medium",
  },
  "Third-Party Tracker Detected": {
    plain: "This page loads an outside tracker that watches your visitors.",
    effort: "Medium",
  },
  "Exposed Sensitive Path": {
    plain: "A sensitive file is publicly reachable and should be blocked.",
    effort: "Medium",
  },
};

export function humanize(issue) {
  const f = FRIENDLY[issue.issueType];
  return {
    plain: f?.plain || issue.description || issue.issueType,
    effort: f?.effort || "Medium",
  };
}
