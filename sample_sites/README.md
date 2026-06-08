# Test Site — Ground Truth

This folder contains a small static site with **intentionally seeded SEO bugs**.
It exists so that we can develop, test and demo the crawler in a controlled
environment that doesn't depend on the public internet.

## How to serve it

From the project root:

```bash
python serve_test_site.py
```

The site is served at `http://localhost:8000`.

## Expected issues — what the analyzer SHOULD detect

| Page | Expected Issues | Severity | Category |
|------|-----------------|----------|----------|
| `/index.html` | none — clean baseline | — | — |
| `/about.html` | Missing Title | High | SEO |
| `/services.html` | Missing H1 | Medium | SEO |
| `/services.html` | Missing Meta Description | Medium | SEO |
| `/pricing.html` | Broken Link (links to `/portfolio.html` which returns 404) | High | SEO |
| `/gallery.html` | 3 × Image Missing Alt | Low | SEO |
| `/contact.html` | none — clean | — | — |
| `/blog.html` | Missing Title (empty `<title>` tag) | High | SEO |
| `/blog.html` | Missing H1 | Medium | SEO |
| `/faq.html` | Slow Response (>2 s, server delays this page by 3 s) | Medium | SEO |
| `/booking.html` | Missing HTML Language | Medium | Accessibility |
| `/booking.html` | Missing Viewport Meta | Medium | Accessibility |
| `/booking.html` | 3 × Form Input Without Label | High | Accessibility |
| `/booking.html` | Generic Link Text ("click here") | Low | Accessibility |
| `/booking.html` | Skipped Heading Level (H2 → H4) | Low | Accessibility |
| `/booking.html` | Button Without Accessible Text | High | Accessibility |
| `/booking.html` | Low Color Contrast (Inline Style) | Low | Accessibility |
| `/offers.html` | Render-Blocking Script (3 scripts in head) | Medium | Performance |
| `/offers.html` | Excessive Inline CSS (>30 KB) | Low | Performance |
| `/offers.html` | Too Many Inline Event Handlers (>10) | Low | Performance |
| `/security.html` | Invalid JSON-LD Syntax (trailing comma) | High | Schema |
| `/security.html` | target=_blank Without rel=noopener | Medium | Security Headers |
| `/security.html` | Mixed Content (http:// img + script) — **HTTPS sites only** | High | Transport Security |

> **Mixed-content note:** the mixed-content check only runs on **https** pages.
> Because the local test site is served over **http**, that issue is masked by
> the higher-priority "Site Not Served Over HTTPS" finding. The seeded `http://`
> resources on `/security.html` exist so the check fires when the same markup is
> scanned on a real HTTPS site.

### Server-level issues (handled by `serve_test_site.py`)

| Path | Behavior | Why |
|------|----------|-----|
| `/portfolio.html` | 404 Not Found | Tests broken-link detection (linked from `/pricing.html`) |
| `/error.html` | 500 Internal Server Error | Tests 5xx status code detection (NOT linked from anywhere — used for direct testing only) |
| `/security.html` | Insecure `Set-Cookie` (no Secure/HttpOnly/SameSite) | Tests cookie checks → flags missing HttpOnly + SameSite (Secure is only required on HTTPS) |

> Because the whole site is served over **http://localhost:8000**, every page
> also produces a **Site Not Served Over HTTPS** finding plus the server's
> **Server header** version disclosure. That is expected — it's what a real
> http site would (correctly) be flagged for.

## Summary — total expected counts

When scanning `http://localhost:8000`, the analyzer should report approximately:

- **~9-11 pages crawled** (index, about, services, pricing, gallery, contact, blog, faq, booking, offers, security)
- **1 broken link** (`/portfolio.html` referenced from `/pricing.html`)
- **2 Missing Title** issues (`about.html`, `blog.html`)
- **2 Missing H1** issues (`services.html`, `blog.html`)
- **1 Missing Meta Description** issue (`services.html`)
- **3 Missing Alt** issues (all on `gallery.html`)
- **1 Slow Response** issue (`faq.html`)
- **Security/Schema issues** on `security.html`: invalid JSON-LD, target=_blank
  without noopener, insecure cookie (HttpOnly + SameSite); plus site-wide
  "Site Not Served Over HTTPS" and Server-header disclosure on every page
- **~60+ issues total** across the site (the security categories add many,
  since no-HTTPS and missing security headers apply to every page)

If the analyzer reports significantly different numbers, something is wrong —
either in the crawler, the analyzer, or this test site.

## Why a local test site?

- **Stable ground truth** — bugs don't change between scans
- **No internet dependency** — demos work offline
- **Fast iteration** — no rate limits, no robots.txt, no etiquette concerns
- **Reproducible tests** — every developer sees the same results

In a real production scenario, the crawler would point at customer websites.
But for development, this controlled site is much more useful.
