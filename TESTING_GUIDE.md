# SitePulse AI — Testing Guide

How to verify everything built in the latest work session:
- **Slow Response Time** moved from SEO → Performance
- **Security (Stage 11)** — four categories: Transport Security, Security
  Headers, Cookies, Information Disclosure (14 checks total)

Work through the three parts in order. Part 1 is the most important.

---

## Part 1 — Automated tests (~30 seconds)

**1. Open a terminal in the project folder and activate the venv:**

```bash
cd "/Users/danswir/Documents/Claude/Projects/Web Health & SEO Crawler"
source venv/bin/activate
```

**2. Run the whole test suite:**

```bash
pytest -q
```

Expected: **`220 passed`**.
(If you see `209`, Python loaded a stale cache — run
`pytest -q -p no:cacheprovider`.)

**3. Run just the security tests, verbosely:**

```bash
pytest tests/test_security.py -v
```

Expected: **41 `PASSED`** lines, grouped into `TestHttps`, `TestHsts`,
`TestMixedContent`, `TestSecurityHeaders`, `TestBlankWithoutNoopener`,
`TestServerHeader`, `TestXPoweredBy`, `TestCookies`, `TestGeneralBehaviour`.

---

## Part 2 — Manual end-to-end on the test site (~2 minutes)

Confirms the crawler really collects headers and cookies from a live site.

**4. In terminal #1, start the test site (leave it running):**

```bash
python serve_test_site.py
```

**5. In terminal #2 (also `source venv/bin/activate`), run the e2e check:**

```bash
python test_e2e_manual.py
```

Expected: a scan of `http://localhost:8000` with `[PASS]` lines.

> Note: the test site runs over **http**, so every page is correctly flagged
> "Site Not Served Over HTTPS" and the Python server's version shows up under
> Information Disclosure. That is expected behaviour, not a bug.

---

## Part 3 — Visual check in the UI (~3 minutes)

Shows the new categories rendering in the dashboard.

**6. Keep the test site running (step 4). In terminal #3, start the UI:**

```bash
streamlit run app.py
```

A browser should open at `http://localhost:8501`.

**7. In the UI:** enter `http://localhost:8000` as the URL and run a scan.

**8. What to look for in the results:**

- In the Issues table's **Category** column, the new categories appear with
  emojis: 🔐 Transport Security, 📢 Information Disclosure (and 🛡️ Security
  Headers / 🍪 Cookies where relevant).
- The category **filter** (multiselect) lists the new categories automatically.
- Filtering by each category updates the table correctly.
- **"Slow Response Time"** now appears under **⚡ Performance** (not 🔍 SEO).
  It comes from `/faq.html`, which simulates a 3-second delay.

---

## If something is off

- **Wrong test count** → stale cache: `pytest -q -p no:cacheprovider`.
- **`ModuleNotFoundError`** → the venv isn't active; re-run
  `source venv/bin/activate`.
- **Port already in use** → another server is still running; stop it (Ctrl+C)
  or change the port.
- **No security issues at all on an HTTPS site** → that can be correct! A
  well-configured site passes these checks. Try scanning the local http test
  site to see the checks fire.

All three parts green = everything from this session works end to end.
