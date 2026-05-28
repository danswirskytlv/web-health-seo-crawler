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

| Page | Expected Issues | Severity |
|------|-----------------|----------|
| `/index.html` | none — clean baseline | — |
| `/about.html` | Missing Title | High |
| `/services.html` | Missing H1 | Medium |
| `/services.html` | Missing Meta Description | Medium |
| `/pricing.html` | Broken Link (links to `/portfolio.html` which returns 404) | High |
| `/gallery.html` | 3 × Image Missing Alt | Low |
| `/contact.html` | none — clean | — |
| `/blog.html` | Missing Title (empty `<title>` tag) | High |
| `/blog.html` | Missing H1 | Medium |
| `/faq.html` | Slow Response (>2 s, server delays this page by 3 s) | Medium |

### Server-level issues (handled by `serve_test_site.py`)

| Path | Behavior | Why |
|------|----------|-----|
| `/portfolio.html` | 404 Not Found | Tests broken-link detection (linked from `/pricing.html`) |
| `/error.html` | 500 Internal Server Error | Tests 5xx status code detection (NOT linked from anywhere — used for direct testing only) |

## Summary — total expected counts

When scanning `http://localhost:8000`, the analyzer should report approximately:

- **8 pages crawled** (index, about, services, pricing, gallery, contact, blog, faq)
- **1 broken link** (`/portfolio.html` referenced from `/pricing.html`)
- **2 Missing Title** issues (`about.html`, `blog.html`)
- **2 Missing H1** issues (`services.html`, `blog.html`)
- **1 Missing Meta Description** issue (`services.html`)
- **3 Missing Alt** issues (all on `gallery.html`)
- **1 Slow Response** issue (`faq.html`)
- **~10 issues total** across the site

If the analyzer reports significantly different numbers, something is wrong —
either in the crawler, the analyzer, or this test site.

## Why a local test site?

- **Stable ground truth** — bugs don't change between scans
- **No internet dependency** — demos work offline
- **Fast iteration** — no rate limits, no robots.txt, no etiquette concerns
- **Reproducible tests** — every developer sees the same results

In a real production scenario, the crawler would point at customer websites.
But for development, this controlled site is much more useful.
