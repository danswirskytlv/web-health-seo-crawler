# SitePulse AI
## Web Health & SEO Crawler with AI Assistant
### Project Book

---

**Students:** Kamil Sason · Dan Swirsky
**Program:** Computer Science, B.Sc.
**Advisor:** (to be filled)
**Institution:** Afeka College of Engineering
**Submission Date:** June 2026

---

## Table of Contents

1. **Executive Summary** ............................................. 3
2. **Adherence to Plan, Compliance and Changes from the Engineering Document** ........ 4
   - 2.1 Changes from the Engineering Document
   - 2.2 Functionality List
   - 2.3 Difficulties Encountered
3. **Methods, Tools and Platforms Selected for System Design and Development** ... 6
   - 3.1 Human-Computer Interfaces
   - 3.2 Class, ERD and UML Diagrams
   - 3.3 Use Cases
   - 3.4 Sequence Diagrams
   - 3.5 Main System Flow Diagram
   - 3.6 Technology Stack
   - 3.7 Architectural Patterns
   - 3.8 Development Methodology
   - 3.9 Software Testing
4. **Architecture** ............................................... 23
   - 4.1 System Overview
   - 4.2 API Specification
   - 4.3 Backend
   - 4.4 Frontend
   - 4.5 Graphical User Interface
   - 4.6 Algorithms
5. **Discussion and Lessons Learned** .............................. 53
   - 5.1 The Idea, Complexity, and Implementation
   - 5.2 Lessons Learned
6. **Summary and Conclusions** ..................................... 54
   - 6.1 Project Summary
   - 6.2 Future Development
7. **References** ................................................. 55
8. **Appendices** ................................................. 56

---

# 1. Executive Summary

This book presents **SitePulse AI** — a multi-category Web Health
diagnostic platform that crawls a website, classifies the issues it
finds across five audit dimensions (SEO, Accessibility, Performance,
Security and Schema), uses Google Gemini to explain each issue in
plain language and to propose a ready-to-paste fix, and persists every
scan to a local database so that the user can compare any two scans
and see what was fixed, what is new, and what is still broken.

The motivation is concrete. Small and mid-sized business owners
routinely lose customers to invisible technical problems on their own
websites: broken links, slow pages, accessibility violations that
silence assistive technologies, missing security headers that expose
the site to clickjacking, and structured-data mistakes that hurt
search visibility. Existing tools surface these problems, but they
do so in language only an engineer can act on. SitePulse AI was built
to bridge that gap end-to-end.

The system is composed of an asynchronous **BFS site crawler** that
respects `robots.txt` and stays within the same domain; an
**analyzer suite** of nine independent rule-based modules that emit
deterministic, severity-tagged issues per category; a **scoring
engine** that computes an explainable per-page health score (0–100)
plus per-category sub-scores; a **persistence layer** built on
SQLite that supports cross-scan diffing; and an **AI layer** built
on Google Gemini that provides three distinct capabilities —
single-issue fix suggestions, root-cause analysis across two scans,
and an "ask your site" conversational chatbot grounded in the most
recent scan data. The system is exposed through a **FastAPI**
backend and consumed by a **React + Vite** single-page application
that runs locally on the user's machine.

A central design principle separates detection from explanation:
the rule-based analyzer is the single source of truth for what
counts as a problem, while the AI is restricted to natural-language
explanation and fix synthesis. This makes the system predictable,
testable and defensible — every point lost on the dashboard maps
to a specific rule that the user can point at.

The implementation comprises approximately **6,300 lines of
production Python**, a complete React frontend, and a test suite
of **369 unit tests** covering URL utilities, every analyzer,
the scoring engine, the persistence layer, all AI modules and
the FastAPI surface. The project was developed iteratively across
two phases: a Streamlit-based prototype proving end-to-end value,
followed by a deeper second phase that introduced multi-category
analysis, persistence, and the production React/FastAPI stack.

---

# 2. Adherence to Plan, Compliance and Changes from the Engineering Document

This chapter compares the original Requirements Document submitted at
the start of the project (`hw3_project.docx`) with what was actually
built. We describe the changes from the engineering document, list
every functional requirement against its delivery status, and
catalogue the technical difficulties we encountered along the way.

The headline conclusion is that the final product not only satisfies
every requirement from the original document but substantially exceeds
its scope. The engineering document defined a single-category SEO
scanner with an AI fix assistant; the final product is a multi-category
Web Health platform spanning SEO, Accessibility, Performance,
Security, Schema and Privacy, with persistent history, scan-to-scan
diffing, root-cause analysis, and an "ask your site" chatbot — and it
runs on a production-grade FastAPI + React stack rather than the
Streamlit prototype originally envisioned.

## 2.1 Changes from the Engineering Document

The engineering document specified three user types (Small Business
Owner, SEO Specialist, Web Developer), a Streamlit-based local desktop
application, and a Python pipeline of "Crawler → Analyzer → AI Agent →
Report". All of these survived to the final product, but with the
substantive deviations summarised in the table below.

| Change | Origin | Approved by | Impact |
| --- | --- | --- | --- |
| Streamlit UI replaced by React + FastAPI | Team | Team | Production-quality SPA, decoupled API, opens future deployment options |
| Single audit category (SEO) expanded to five | Team | Team | The product is now a Web Health platform, not just an SEO scanner |
| Per-category sub-scores added on top of the global 0–100 score | Team | Team | Users can act on weak categories without parsing a long issue list |
| Local SQLite persistence and scan history | Team | Team | Enables diffing, trend charts and root-cause analysis |
| AI scope expanded from "fix one issue" to three assistants (fix, root-cause, chatbot) | Team | Team | Significantly stronger differentiation against existing tools |
| OpenAI replaced by Google Gemini | Team | Team | Free-tier quota suitable for a student project; same JSON-schema discipline |
| Default crawler ceiling lowered from 200 pages in 60 s to 50 pages by default (adjustable) | Team | Team | Safer defaults; the original 200/60 s target remains achievable |
| "Headless Mode" for the Web Developer use case dropped | Team | Team | The Issues screen's category filter satisfies the same use case more directly |

The first change — the migration from a Streamlit prototype to a
React + FastAPI production stack — is the single most consequential
one. It was the result of a deliberate two-phase development plan: a
Streamlit prototype proved the end-to-end value of the idea, and the
second phase rebuilt the user interface on a foundation that we could
defend as a real product. The migration was made tractable by the
strict separation of concerns described in Section 4.1: the crawler,
analysers, scoring engine and persistence layer were re-used without
modification.

The expansion from a single SEO category to five was driven by the
realisation that small business owners do not actually distinguish
between "my SEO is broken" and "my site is slow" or "my site is
inaccessible" — they perceive a single feeling of an unhealthy site.
Once we had implemented the SEO analyser, adding Accessibility
(WCAG-style checks), Performance (page weight, render-blocking
scripts, resource counts), Security (HTTPS, security headers, cookies,
information disclosure), Schema (JSON-LD validity) and Privacy
(third-party trackers) became a matter of writing new pure-function
detectors in the same architectural pattern. The framework, in other
words, encouraged extension.

The choice of Google Gemini over OpenAI (mentioned as an example in
the engineering document) was made for two reasons: Gemini's free
tier was sufficient for a student project budget, and Gemini's
adherence to a structured JSON output schema proved reliable enough
to anchor our four-field response contract. The architectural
isolation of the AI layer (Section 4.3.4) means that switching to a
different LLM provider would be a localised modification.

## 2.2 Functionality List

The table below lists every functional requirement, explicit or
implicit, in the original engineering document, alongside its delivery
status and the module in which it was implemented.

### 2.2.1 Functional Requirements from the Engineering Document

| Requirement | Status | Implemented in |
| --- | --- | --- |
| Crawl internal pages of a given domain | Achieved | `crawler/crawler.py` |
| Same-domain restriction (no external crawl) | Achieved | `crawler/url_utils.py` (`is_internal_url`) |
| Respect `robots.txt` | Achieved | `crawler.RobotsChecker` |
| Detect missing `<title>` tags | Achieved | `analyzer/seo_analyzer.py` |
| Detect missing `<h1>` tags | Achieved | `analyzer/seo_analyzer.py` |
| Detect missing meta description | Achieved | `analyzer/seo_analyzer.py` |
| Detect images without `alt` text | Achieved | `analyzer/seo_analyzer.py` |
| Detect broken links (4xx) | Achieved | `analyzer/seo_analyzer.py` (cross-page) |
| Detect server errors (5xx) | Achieved | `analyzer/seo_analyzer.py` |
| Detect slow response times | Achieved | `analyzer/seo_analyzer.py` and `performance.py` |
| Compute a 0–100 health score | Achieved | `analyzer/scoring.py` |
| AI agent that explains each issue | Achieved | `ai/ai_assistant.py` |
| AI agent that suggests a fix snippet | Achieved | `ai/ai_assistant.py` (`code_snippet` field) |
| Visual user interface (non-CLI) | Achieved | React + Vite SPA |
| Export results as a PDF report | Achieved | `reports/pdf_exporter.py` |
| Local execution (no cloud dependency) | Achieved | FastAPI + SQLite on `localhost` |

### 2.2.2 Functionality Added Beyond the Engineering Document

| New capability | Reason added | Implemented in |
| --- | --- | --- |
| Accessibility audit (WCAG-style checks) | Web health is not just SEO | `analyzer/accessibility.py` |
| Performance audit (page weight, render-blocking, etc.) | Same | `analyzer/performance.py` |
| Security audit (HTTPS, headers, cookies, disclosure) | Same | `analyzer/security.py`, `tls.py`, `exposed_paths.py` |
| Schema.org structured-data validation | Search visibility is a core SEO concern | `analyzer/schema_org.py` |
| Privacy / third-party tracker detection | GDPR-adjacent issue worth surfacing | `analyzer/privacy.py` |
| Per-category sub-scores | Lets users prioritise across categories | `analyzer/scoring.py` |
| Persistent scan history (SQLite) | Enables trend analysis | `database/db.py` |
| Scan-to-scan diff (fixed / new / unchanged) | The user wants to see progress, not absolutes | `database.get_diff` |
| AI root-cause analysis across two scans | Explains what likely changed in the codebase | `ai/root_cause.py` |
| AI chatbot ("ask your site") | Open-ended Q&A grounded in scan data | `ai/chatbot.py` |
| CSV exports (issues, pages) | SEO specialists asked for tabular data | `reports/csv_exporter.py` |
| HTTP API (FastAPI) | Decouples UI from analysis logic | `api/main.py` |
| React + Vite single-page application | Production-quality presentation tier | `frontend/` |

### 2.2.3 Non-Functional Requirements

The engineering document listed three non-functional requirements with
explicit success metrics. The table below records each one against
its measured outcome on the bundled test site.

| Non-functional requirement | Engineering document target | Measured outcome |
| --- | --- | --- |
| AI response latency | < 5 s, contextually relevant | ~2–4 s on Gemini Flash, response constrained to a four-field JSON contract |
| Crawler throughput | 200 pages in < 60 s (multi-threaded) | Achievable with `max_workers=8` on a modest broadband link; default ceiling lowered to 50 to make the typical scan feel snappy |
| HTTP status accuracy | 100% accuracy, no false positives | Achieved; both 4xx and 5xx are classified deterministically with no ambiguity |

## 2.3 Difficulties Encountered

This section catalogues the most consequential technical difficulties
we encountered during development. Each entry follows the same
structure: a description of the problem, the solution we adopted, and
the lesson we drew from it.

### 2.3.1 URL Normalisation Caused Duplicate Crawls

**Problem.** Early in the crawler's life we discovered that the same
logical page was being visited multiple times through three different
URLs — `http://localhost:8000`, `http://localhost:8000/`, and
`http://localhost:8000/index.html`. The visited set treated each
string as distinct, which inflated page counts and broke the
broken-link detection downstream.

**Solution.** We introduced `normalize_url` (Section 4.6.1), a pure
function that produces a canonical form for every URL. It is now
called both when seeding the crawler with the root URL and when
discovering new links inside pages. Every URL the visited set sees
has already been normalised.

**Lesson.** Identity comparisons in a distributed system (and a
crawler is a small distributed system) are dangerous when the inputs
are user-controlled strings. Defining a canonical form once,
upstream of every comparison, is cheaper than chasing the
consequences of inconsistency.

### 2.3.2 Slow Single-Page Behaviour Blocked the Whole Crawl

**Problem.** Our bundled test site intentionally includes one page
(`/faq.html`) that delays its response by three seconds, to allow us
to verify the slow-response detector. The original single-threaded
HTTP server delivered this delay correctly, but because it processed
requests serially the entire crawl appeared to take six or seven
seconds longer than it should have.

**Solution.** We rewrote the bundled test server to use
`ThreadingHTTPServer` so that the slow page no longer blocks every
other request. The crawler itself was always concurrent; the
bottleneck was on the server side.

**Lesson.** A test fixture can mask the real performance of the
system. We could only see the concurrency benefit of the crawler
once the test site was capable of serving requests concurrently too.

### 2.3.3 Gemini Sometimes Returns JSON Wrapped in Code Fences

**Problem.** Our prompt template asks Gemini to return a strict
four-field JSON object. Most of the time the model complies, but
occasionally it wraps the JSON in a markdown ` ```json ` code fence
or adds a one-line preface. Naive `json.loads(response.text)` calls
raised exceptions.

**Solution.** We wrote a defensive parser that extracts the outermost
balanced `{...}` block, strips any surrounding markdown, validates the
expected keys, and falls back to a deterministic answer if any step
fails. The fallback uses the analyser's own description and
recommendation, so the user always sees a useful answer.

**Lesson.** LLM output should be treated as untrusted input. The
parser sits at the boundary between the model and the rest of the
system, and it is the only place that needs to know about model
quirks.

### 2.3.4 Free-Tier Quota Exhaustion on `gemini-2.0-flash`

**Problem.** We initially targeted `gemini-2.0-flash` as the default
model. During a demo we discovered that the free tier for that
specific model had been disabled, returning HTTP 429 errors. The
fallback path worked correctly but no longer leveraged the AI.

**Solution.** We made the model name configurable via the
`GEMINI_MODEL` environment variable and switched the default to
`gemini-flash-latest`, which has a generous free tier. We also
introduced a per-session call limit (`AI_MAX_CALLS_PER_SESSION`) so
that an enthusiastic user cannot accidentally exhaust the quota
themselves.

**Lesson.** API providers tighten their free tiers without warning.
Externalising the model name and capping the call rate are both cheap
investments that buy resilience against vendor decisions.

### 2.3.5 Migrating the UI Without Breaking the Backend

**Problem.** Between Phase 1 and Phase 2 we replaced the entire
presentation tier — moving from Streamlit (Python, server-rendered)
to React + Vite (JavaScript, client-rendered) plus a FastAPI bridge.
A typical risk in such migrations is that backend code starts to leak
into the UI layer, or that the API surface ends up reflecting the
quirks of one specific frontend.

**Solution.** We treated the migration as a forcing function for
discipline. The serialisation layer (`api/serializers.py`) was
written as a separate concern from the analytical code, and the React
frontend was forbidden from importing anything Python-specific. All
domain objects continued to flow through the same `Issue` / `Page`
/ `ScanResult` / `ScanDiff` dataclasses; only their JSON
representations were new.

**Lesson.** A well-defined dataclass boundary is the cheapest
insurance against future UI churn. The Streamlit-era code in
`crawler/`, `analyzer/`, `database/`, `ai/` and `reports/` was
re-used by the new API tier verbatim.

### 2.3.6 Right-to-Left Text Bleeding Into English Layouts

**Problem.** When we used a Hebrew Afeka poster template as the
starting point for the academic poster, the inherited paragraph
direction was right-to-left. English text rendered on top of that
template had its colons and periods migrate to the left side of the
line, which looked broken.

**Solution.** We forced an explicit `rtl="0"` and `lang="en-US"` on
every text run produced by our PowerPoint generator. The fix was
small but only discoverable by rendering the slide and looking at it.

**Lesson.** Internationalisation defaults are sticky. When a tool
inherits a template, it inherits the template's locale; making the
locale explicit is the only reliable way to override it.

---

# 3. Methods, Tools and Platforms Selected for System Design and Development

This chapter describes the methods, tools and platforms that were
chosen to build SitePulse AI. It begins with the user-facing
interfaces, descends through the structural and behavioural
diagrams that guided the design, and ends with the technology
stack, architectural patterns, development methodology and testing
strategy.

## 3.1 Human-Computer Interfaces

SitePulse AI is designed for three distinct user roles identified in
the engineering document. Each role uses a different subset of the
same React interface; nothing in the UI is role-aware in code, but
the visual hierarchy of the screens guides each role to the
information they need.

The **Small Business Owner** lands on the Scan screen, runs a scan,
and is taken to the post-scan dashboard. The visual prominence of
the circular `ScoreGauge`, the colour-coded grade label, and the
"Ask AI" button on every issue is calibrated to this user: they do
not need to read raw issue lists; they need a single judgement
("your site is in Good shape") and a click-through path to a
plain-language fix.

The **SEO Specialist** uses the Issues screen and the Reports screen
heavily. The Issues table supports multi-select severity and
category filters and a free-text search so that a specialist
auditing a 200-page client site can isolate "all High-severity SEO
issues on the blog" in a few clicks. The Reports screen exposes
CSV and PDF exports that match this user's deliverable expectations.

The **Web Developer** uses the History screen and the Chat screen.
History supports cross-scan diffing — "what broke between yesterday
and today" — which is the developer's natural framing post-deploy.
Chat lets the developer ask open-ended questions like "are there any
new 5xx errors on the API routes?" without leaving the dashboard.

All interactions take place inside a normal desktop browser at
`http://localhost:5173`. There are no mobile-specific views: the
target audience runs SitePulse on a workstation while they work on
their site, not while they are away from it.

## 3.2 Class, ERD and UML Diagrams

This section presents the structural diagrams of the system: the
class diagram of the domain dataclasses, the entity–relationship
diagram of the SQLite store, and a high-level UML diagram of the
package dependencies.

### 3.2.1 Class Diagram (Domain Dataclasses)

The five typed dataclasses in `models/result_models.py` form the
spine of the system. Every analyser produces them, the database
persists them, the AI consumes them, the API serialises them, and
the React frontend renders them.

```
+-----------------+        +-----------------+        +------------------+
|   PageResult    |  *--1  |   ScanResult    |  1--*  |      Issue       |
+-----------------+        +-----------------+        +------------------+
| url             |        | root_url        |        | url              |
| status_code     |        | pages           |        | issue_type       |
| response_time   |        | issues          |        | severity         |
| response_size   |        | score           |        | category         |
| content_type    |        +-----------------+        | description      |
| headers (T)     |                 1                 | recommendation   |
| html (T)        |                 |                 | status_code      |
| links (T)       |                 |                 | response_time    |
| error           |                 v                 +------------------+
+-----------------+        +-----------------+
                           |  ScoreResult    |
                           +-----------------+
                           | score (0..100)  |
                           | grade           |
                           | high_count      |
                           | medium_count    |
                           | low_count       |
                           | category_scores |
                           +-----------------+

+-----------------+        +-----------------+
|  ScanSummary    |        |    ScanDiff     |
+-----------------+        +-----------------+
| id              |        | from_scan       |
| root_url        |        | to_scan         |
| scanned_at      |        | fixed_issues    |
| score, grade    |        | new_issues      |
| high/med/low_   |        | unchanged_      |
|   count         |        |   issues        |
| avg_response_   |        | score_delta     |
|   time          |        +-----------------+
+-----------------+
```

`(T)` marks fields that are kept only transiently in memory — they
are produced by the crawler and consumed by the analyser, but they
are deliberately not persisted to disk. `ScanSummary` is a
lightweight projection of `ScanResult` used by the History screen
when it does not need pages or issues. `ScanDiff` is the cross-scan
comparison object produced by `database.get_diff`.

### 3.2.2 Entity–Relationship Diagram

The SQLite store has four tables, related by foreign keys with
`ON DELETE CASCADE` semantics:

```
+-----------+ 1     N +---------+
|   scans   |---------|  pages  |
+-----------+         +---------+
      | 1
      |
      | N           +---------+
      +-------------|  issues |
      |             +---------+
      | 1
      |
      | N           +-------------------+
      +-------------|  category_scores  |
                    +-------------------+
```

`scans` is the parent table; each row stores the metadata for one
completed scan (root URL, timestamp, global score, grade, severity
counts, average response time). `pages` and `issues` are
child tables, each row referencing a `scans.id`. `category_scores`
is a thin join table mapping `(scan_id, category)` to a sub-score
between 0 and 100. Cascade deletion guarantees that
`DELETE FROM scans WHERE id = ?` removes every dependent row in one
statement.

### 3.2.3 Package Dependency Diagram (UML, simplified)

The nine domain packages depend on each other strictly in one
direction:

```
                      +----------+
                      | frontend |
                      | (React)  |
                      +----+-----+
                           | HTTP
                           v
                       +---+---+
                       |  api  |    (FastAPI app + serializers)
                       +---+---+
                           |
            +--------------+--------------+
            |              |              |
            v              v              v
       +---------+   +-----------+   +---------+
       | crawler |   | analyzer  |   |   ai    |
       +----+----+   +-----+-----+   +----+----+
            |              |              |
            +-----+--------+--------+-----+
                  |                 |
                  v                 v
              +---------+      +---------+
              | models  |<-----| database |
              +---------+      +---------+
                                    |
                                    v
                              +----------+
                              | reports  |
                              +----------+
```

`models` sits at the bottom of the diagram because every other
package depends on it. `api` sits at the top because nothing
depends on it. This acyclic structure is why the migration from
Streamlit to React + FastAPI (Section 2.1) was possible without
touching any of the analytical code.

## 3.3 Use Cases

The use cases below correspond to the three user roles introduced
in the engineering document. Each use case lists its
pre-conditions, the user's interaction, the system's response, and
the post-condition.

### 3.3.1 UC-1: Small Business Owner Fixes a Missing Title

- **Pre-condition.** The user knows their site looks bad on Google
  search but does not know what is wrong.
- **Interaction.** The user opens SitePulse, enters the site URL on
  the Scan screen, clicks "Run scan", waits ~5 seconds, sees a
  Critical grade with a "Missing Title" issue on the home page,
  and clicks "Ask AI" on that row.
- **System response.** The frontend opens the `AiFixDrawer`, which
  posts the issue to `POST /api/ai/fix`. Gemini returns a
  four-field JSON: a simple explanation, why it matters, a suggested
  fix, and a copy-paste `<title>` snippet.
- **Post-condition.** The user has a ready-to-paste HTML snippet
  and can update their site in their CMS.

### 3.3.2 UC-2: SEO Specialist Audits a 200-Page Client Site

- **Pre-condition.** The specialist needs a monthly audit deliverable.
- **Interaction.** The specialist enters the URL, sets
  `max_pages=200` and `max_depth=4` on the Scan screen, runs the
  scan, opens the Issues screen, filters to High-severity issues
  only, then opens the Reports screen and downloads the PDF report.
- **System response.** The crawler runs concurrently, the analysers
  produce a categorised issue list, the PDF exporter generates a
  print-ready report with a coloured severity table.
- **Post-condition.** The specialist sends the PDF to their client.

### 3.3.3 UC-3: Web Developer Diffs Two Scans After a Deployment

- **Pre-condition.** The developer has just deployed a new build of
  the blog template and wants to confirm it did not regress.
- **Interaction.** The developer opens the History screen, picks
  the scan from this morning and the scan from yesterday, clicks
  "Diff".
- **System response.** The frontend calls `GET /api/diff`, the
  backend returns a `ScanDiff` partitioning issues into fixed, new
  and unchanged. The developer then clicks "Get root cause", which
  posts the diff to `POST /api/ai/root-cause`.
- **Post-condition.** The developer reads an AI-generated paragraph
  explaining that all five new broken links cluster in `/blog/`, and
  reverts the deployment.

## 3.4 Sequence Diagrams

The three sequence diagrams below trace the most consequential
flows through the system, in plain text form.

### 3.4.1 Sequence: Run a Scan

```
User      Browser      FastAPI         crawler    analyzer    database
 |  type   |              |              |          |          |
 |-------->|              |              |          |          |
 |  click  |              |              |          |          |
 |-------->| POST /api/   |              |          |          |
 |         |   scan       |              |          |          |
 |         |------------->|              |          |          |
 |         |              | crawl_site() |          |          |
 |         |              |------------->|          |          |
 |         |              |  pages       |          |          |
 |         |              |<-------------|          |          |
 |         |              | analyze_pages|          |          |
 |         |              |---------------------->  |          |
 |         |              |  issues                 |          |
 |         |              |<----------------------- |          |
 |         |              | calculate_score()       |          |
 |         |              |---------------------->  |          |
 |         |              |  score                  |          |
 |         |              |<----------------------- |          |
 |         |              | save_scan()                        |
 |         |              |----------------------------------->|
 |         |              |  scan_id                           |
 |         |              |<-----------------------------------|
 |         | JSON         |              |          |          |
 |         |<-------------|              |          |          |
 | render  |              |              |          |          |
 |<--------|              |              |          |          |
```

### 3.4.2 Sequence: Ask AI for a Fix

```
User    Browser     FastAPI       ai/ai_assistant     Gemini API
 | click  |            |                  |               |
 |------->| POST /api/ |                  |               |
 |        |  ai/fix    |                  |               |
 |        |----------->|                  |               |
 |        |            | generate_ai_fix()|               |
 |        |            |----------------->|               |
 |        |            |                  | generate_     |
 |        |            |                  |  content()    |
 |        |            |                  |-------------->|
 |        |            |                  |   JSON reply  |
 |        |            |                  |<--------------|
 |        |            |                  | parse + validate
 |        |            |  AIResponse      |               |
 |        |            |<-----------------|               |
 |        | JSON       |                  |               |
 |        |<-----------|                  |               |
 | render |            |                  |               |
 |<-------|            |                  |               |
```

If `Gemini API` is unavailable, `ai_assistant` falls back to a
deterministic response derived from the analyser's recommendation;
the user still sees an `AIResponse`.

### 3.4.3 Sequence: Diff Two Saved Scans

```
User      Browser      FastAPI         database
 |   pick   |             |               |
 |--------->| GET /api/   |               |
 |          |   diff?     |               |
 |          |   from=x&   |               |
 |          |   to=y      |               |
 |          |------------>|               |
 |          |             | get_diff(x,y) |
 |          |             |-------------->|
 |          |             |  ScanDiff     |
 |          |             |<--------------|
 |          | JSON        |               |
 |          |<------------|               |
 |  render  |             |               |
 |<---------|             |               |
```

## 3.5 Main System Flow Diagram

The end-to-end runtime flow of a single scan is shown below. Each
arrow corresponds to a function call across a package boundary.

```
   +-------------+      +--------------+      +---------------+
   |   User      |--+-->| React        |----->| FastAPI        |
   |   Browser   |  |   | (Vite SPA)   |      | (api/main.py)  |
   +-------------+  |   +--------------+      +-------+-------+
                    |                                 |
                    | (1) POST /api/scan              |
                    |                                 |
                    |                                 v
                    |                          +--------------+
                    |                          | crawler.     |
                    |                          | crawl_site() |
                    |                          +------+-------+
                    |                                 |
                    |                                 v
                    |                          +---------------+
                    |                          | analyzer.     |
                    |                          | analyze_pages |
                    |                          |   |           |
                    |                          |   v           |
                    |                          | seo, a11y,    |
                    |                          | perf, sec,    |
                    |                          | schema, ...   |
                    |                          +------+--------+
                    |                                 |
                    |                                 v
                    |                          +---------------+
                    |                          | scoring.      |
                    |                          | calculate_    |
                    |                          |   score()     |
                    |                          +------+--------+
                    |                                 |
                    |                                 v
                    |                          +---------------+
                    |                          | database.     |
                    |                          | save_scan()   |
                    |                          +------+--------+
                    |                                 |
                    |  (2) JSON ScanResult            |
                    |<--------------------------------+
                    v
              Render dashboard
```

The user's optional follow-on actions (Ask AI, download PDF, diff
two scans, chat) each trigger one more round-trip through the
`(1)` / `(2)` pattern with a different endpoint.

## 3.6 Technology Stack

The stack was chosen so that every layer is mainstream, well
documented, and free for student use. No proprietary services are
required.

### 3.6.1 Backend Stack

| Concern | Choice | Version | Justification |
| --- | --- | --- | --- |
| Language | Python | 3.10+ | Mature ecosystem, fast iteration |
| Web framework | FastAPI | 0.115.0 | Auto-generated OpenAPI docs, async-ready, strong typing |
| ASGI server | Uvicorn | 0.30.6 | Standard FastAPI deployment target |
| HTTP client | requests | 2.32.3 | Industry standard for synchronous HTTP |
| HTML parsing | BeautifulSoup4 + lxml | 4.12.3 / 5.3.0 | Forgiving parser; copes with real-world HTML |
| Concurrency | `concurrent.futures.ThreadPoolExecutor` | stdlib | Right model for network-bound work |
| TLS / certificates | `ssl`, `certifi` | stdlib / 2024.8.30 | Real certificate validation |
| LLM | Google Gemini | google-generativeai 0.8.3 | Generous free tier; reliable JSON output |
| Database | SQLite | stdlib | Zero-config; single file; perfect for desktop |
| PDF | ReportLab | 4.2.5 | Mature; produces print-quality output |
| Config | python-dotenv | 1.0.1 | Reads `.env` files without leaking secrets to git |
| Testing | pytest | 8.3.3 | Industry-standard framework |
| API testing | httpx | 0.27.2 | FastAPI TestClient dependency |

### 3.6.2 Frontend Stack

| Concern | Choice | Version | Justification |
| --- | --- | --- | --- |
| Framework | React | 18.3.1 | Industry standard; abundant talent pool |
| Build tool | Vite | 5.4.8 | Sub-second hot reload; minimal config |
| Routing | react-router-dom | 6.26.2 | Standard React routing primitives |
| Charts | Recharts | 2.12.7 | Lightweight; declarative; matches React idioms |
| Styling | Hand-written CSS | n/a | No design system dependency; every visual element is explicable |

### 3.6.3 Tooling

- **Version control:** Git, hosted on GitHub.
- **IDE:** PyCharm (Python) and VS Code (frontend) by personal
  preference, with no project-specific lock-in.
- **Operating system:** macOS for development; the platform itself
  is OS-agnostic and was smoke-tested on Linux.

## 3.7 Architectural Patterns

Three architectural patterns shape the codebase.

**Layered architecture.** The presentation tier (React) depends on
the application tier (FastAPI), which depends on the domain modules
(`crawler`, `analyzer`, `database`, `ai`, `reports`), which depend
on the shared models. Each layer exposes a stable contract; each
layer can be replaced without touching the layers below it. The
Phase-1-to-Phase-2 migration (Streamlit → React/FastAPI) replaced
the presentation tier without touching any domain module.

**Pipes and filters.** Inside the analyser package, each detector
is a pure function from a list of `PageResult` objects to a list
of `Issue` objects. `analyze_pages` is the pipeline that
concatenates them. Adding a new analyser means writing a new
filter; nothing else changes.

**Repository pattern.** The `database/db.py` module exposes a
small DAO surface (`save_scan`, `list_scans`, `get_scan`,
`delete_scan`, `get_diff`) and hides every SQL statement behind it.
The rest of the system talks in `ScanResult` / `ScanSummary` /
`ScanDiff` dataclasses and never sees a SQL row.

## 3.8 Development Methodology

We worked in an iterative, two-phase model.

**Phase 1 — Prototype.** We delivered a vertical slice of the
product on a Streamlit UI: a single-category SEO analyser, a
crawler, a scoring engine, an AI fix assistant, CSV and PDF
exports, and a tests-from-day-one discipline. The prototype was
demonstrable end-to-end before any additional categories were
added.

**Phase 2 — Productisation.** With the prototype proven, we
rewrote the presentation tier on React + Vite + FastAPI, added four
new analyser categories (Accessibility, Performance, Security,
Schema), introduced the SQLite persistence layer, and built the
two AI assistants (root-cause and chatbot) on top of it.

Throughout both phases we followed a small set of disciplines:

- **One concern per commit.** Each git commit was small and
  cohesive; the final history tells the build story step-by-step.
- **Pure functions wherever possible.** URL utilities, analyser
  rules, scoring and serialisation are all pure; their tests run
  in milliseconds.
- **Dataclasses at every package boundary.** The same
  `Issue` object that an analyser creates is the same object the
  database persists and the AI consumes. There is no second
  internal representation.
- **Reproducible test site.** A bundled test site
  (`sample_sites/test_site/`) contains intentionally seeded bugs in
  every audit category, so that the entire pipeline can be
  exercised end-to-end without depending on the public Internet.

## 3.9 Software Testing

The test suite is the safety net that made the second phase
possible. Without it, every refactor in the migration from
Streamlit to React would have introduced regressions; with it, the
analyser, scoring and persistence layers were re-used verbatim.

### 3.9.1 Test Inventory

The test suite contains **369 unit tests** across 16 files, with a
total runtime of well under a second on a modern laptop.

| File | Tests | Subject |
| --- | --- | --- |
| `test_url_utils.py` | 41 | URL normalisation, internal-link detection, link extraction |
| `test_analyzer.py` | 28 | SEO analyser rules |
| `test_accessibility.py` | 31 | WCAG-style accessibility rules |
| `test_performance.py` | 26 | Page weight, render-blocking scripts, resource counts |
| `test_security.py` | 55 | HTTPS, security headers, cookies, info disclosure |
| `test_tls.py` | 20 | Certificate expiry, weak TLS versions, hostname mismatch |
| `test_schema.py` | 24 | JSON-LD validation and type recommendations |
| `test_privacy.py` | 12 | Known third-party tracker detection |
| `test_exposed_paths.py` | 9 | Sensitive-path probing |
| `test_scoring.py` | 29 | Global and per-category score computation |
| `test_database.py` | 28 | DAO round-trips and diffing |
| `test_serializers.py` | 16 | Dataclass-to-JSON serialisation |
| `test_reports.py` | 12 | CSV / PDF export shape |
| `test_api.py` | 12 | FastAPI endpoints via TestClient |
| `test_chatbot.py` | 11 | Chatbot context building and Gemini integration |
| `test_root_cause.py` | 15 | Diff clustering and root-cause analysis |
| **Total** | **369** | |

### 3.9.2 Testing Strategy

The test suite follows two principles.

**Tests are isolated.** Every test either constructs its inputs
in-memory or uses a per-test temporary file. There is no shared
mutable state, no fixture ordering dependency and no need for the
test site to be running. The `tests/test_database.py` file uses
`tempfile.mkstemp` to give each test its own SQLite file, deleted
in the teardown.

**External services are mocked.** Tests for the AI modules
(`test_chatbot.py`, `test_root_cause.py`) and tests that exercise
TLS (`test_security.py`, `test_tls.py`) use mocks rather than
real network calls. This keeps the suite fast, deterministic, and
runnable offline.

### 3.9.3 Test Categories

We classify each test into one of three categories.

- **Pure unit tests** verify a single function on a small in-memory
  input. The majority of tests are of this kind.
- **Round-trip tests** verify that data survives a journey through
  the system: a `ScanResult` saved to SQLite and loaded back should
  equal the original (modulo intentionally not-persisted fields).
- **Integration tests** verify that a sequence of operations
  produces the expected behaviour: `test_api.py` posts a scan
  request to the FastAPI TestClient and asserts on the response
  shape.

### 3.9.4 What the Test Suite Does Not Cover

We are explicit about the limits of the suite. The frontend is not
unit-tested; we relied on manual testing in the browser. End-to-end
tests that drive a real browser (e.g., Playwright) were considered
but deferred. Live network calls to Gemini are not part of the
suite; the prompt and parsing layers are tested deterministically
with mocked responses. These are the natural next steps for a
follow-on iteration of the project.

---

# 4. Architecture

This chapter describes the architecture of SitePulse AI in detail. We
begin with a high-level overview of the system and the design principle
that drives every decision below it, then descend layer by layer: the
HTTP API surface, the backend modules, the React frontend, the user
interface, and finally the non-trivial algorithms.

## 4.1 System Overview

SitePulse AI is a desktop-oriented Web Health auditing platform. The
user runs three local processes on their machine: a FastAPI service
that exposes the analytical capabilities, a small static test site used
for development and demos, and a Vite-served React single-page
application that consumes the API. Conceptually the system is a
classic three-tier architecture — presentation, application, and data —
deliberately kept on a single machine to avoid every concern that
multi-tenant SaaS would introduce.

### 4.1.1 Tiers

The **presentation tier** is a React 18 single-page application built
with Vite and React Router. It is composed of nine screens
(Landing, Overview, Scan, Issues, Reports, History, Chat, Settings, and a
generic Placeholder) and reusable components (`Sidebar`, `PageHeader`,
`ScoreGauge`, `AiFixDrawer`, `Logo`). All state is held in React hooks
and a small `state` module; there is no global Redux store, because
the application is read-mostly and most data flows from API responses.

The **application tier** is a FastAPI service exposed on port 8001.
It exposes eleven HTTP endpoints (Section 4.2) and is itself a thin
adapter: each endpoint deserialises the request, delegates to one of
the domain modules (`crawler`, `analyzer/*`, `database`, `ai/*`,
`reports`), and serialises the response. All the analytical and AI
behaviour lives in those domain modules, not in the API layer.

The **data tier** is a local SQLite database (`sitepulse.db`) sitting
next to the project root. It stores every saved scan, the pages and
issues that belong to it, and a per-category sub-score table that was
added when multi-category audits were introduced. SQLite was chosen
deliberately over a server-class database: a single-user desktop tool
that the user can copy, back up and inspect with any free SQLite
viewer is more valuable than a cloud database that imposes a server
and an account.

### 4.1.2 Domain Modules

Inside the application tier, the code is split into nine domain
packages that mirror the responsibilities of the system:

| Package | Responsibility |
| --- | --- |
| `crawler/` | BFS site crawl with concurrency, robots.txt and URL normalization |
| `analyzer/` | Nine independent rule-based detectors plus the scoring engine |
| `models/` | Shared typed dataclasses (`PageResult`, `Issue`, `ScoreResult`, `ScanResult`) |
| `database/` | SQLite schema, DAO functions, scan-to-scan diffing |
| `ai/` | Gemini integration: prompts, fix assistant, root-cause, chatbot |
| `reports/` | CSV and PDF exporters |
| `api/` | FastAPI app, request/response serialisers |
| `frontend/` | React SPA (separate process under Vite) |
| `tests/` | pytest suite covering every module above |

Each package depends only on those above it in this list. The
`analyzer/` and `database/` packages, for example, do not know that an
HTTP API exists; they could be re-exposed through a CLI or a Streamlit
UI without modification. This is the property that made the migration
from the original Streamlit prototype to the React/FastAPI stack
feasible without rewriting any analyser or model.

### 4.1.3 The Detection-vs-Explanation Principle

A single design principle drives the entire system: **detection is
rule-based and deterministic; the AI only explains**. Every issue
visible to the user came from one of the nine analysers, each of which
is a pure function from `PageResult` to `list[Issue]`. The AI is never
asked "is this a problem?", only "this is a problem — please explain
it and suggest a fix".

The motivation is practical. Large language models are creative,
which is a liability when the goal is to convince a website owner that
their site has exactly the problems we claim it does. By contrast,
rule-based detectors are auditable: every issue maps to a specific
function in a named file, every threshold maps to a constant the user
can inspect, and every penalty point on the dashboard maps to a single
rule firing. The AI's role — translating those rules into natural
language and synthesising a fix — is exactly the part it is good at.

This principle has two architectural consequences. First, the
`analyzer/` package has no dependency on `ai/`. Second, every
`ai/` module accepts pre-classified inputs (`Issue` objects, `ScanDiff`
objects, `ScanResult` objects) and never produces them.

### 4.1.4 Data Flow End-to-End

A typical scan flows through the system as follows.

1. The user enters a URL on the **Scan screen** of the React UI and
   clicks "Run scan".
2. The browser issues `POST /api/scan` with the URL and a small set of
   options (max pages, depth, timeout, polite delay).
3. The API endpoint calls `crawler.crawl_site(...)`, which performs a
   BFS crawl over the same-domain pages and returns `list[PageResult]`.
4. The API then calls `analyzer.analyze_pages(...)`, which fans out to
   each of the nine analysers and concatenates their `Issue` lists.
5. The API calls `analyzer.scoring.calculate_score(...)` to produce
   the global 0–100 score, the four grade bands, and per-category
   sub-scores.
6. The result is wrapped in a `ScanResult` dataclass and persisted via
   `database.save_scan(...)`, returning a `scan_id`.
7. The API serialises the `ScanResult` and returns it as JSON.
8. The React app receives the result, navigates to the **Overview
   screen**, and renders the dashboard cards, the `ScoreGauge`, the
   issues table grouped by category, and per-category sub-score bars.
9. From any issue, the user can open the **AI Fix Drawer**
   (`AiFixDrawer.jsx`), which posts the selected issue to
   `POST /api/ai/fix` and renders the structured response (simple
   explanation, why it matters, suggested fix, code snippet).
10. The user can revisit the scan later from the **History screen**,
    diff it against an earlier scan via `GET /api/diff`, or ask
    open-ended questions via the **Chat screen**.

## 4.2 API Specification

The application tier exposes eleven HTTP endpoints under the `/api/`
prefix, grouped into four functional areas: health, scanning,
historical access and AI. All endpoints return JSON unless an explicit
file is requested (CSV, PDF). All endpoints are local-only — no
authentication is required because the API is bound to `localhost` and
not exposed to the network.

### 4.2.1 Endpoint Catalogue

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Liveness probe |
| `POST` | `/api/scan` | Run a new scan, optionally save it |
| `GET` | `/api/scans` | List saved scans, newest first |
| `GET` | `/api/scans/{scan_id}` | Reconstruct one saved scan |
| `GET` | `/api/diff` | Diff two saved scans |
| `GET` | `/api/scans/{scan_id}/report/issues.csv` | CSV of issues |
| `GET` | `/api/scans/{scan_id}/report/pages.csv` | CSV of crawled pages |
| `GET` | `/api/scans/{scan_id}/report/report.pdf` | Print-ready PDF |
| `POST` | `/api/ai/fix` | Ask AI to explain and fix one issue |
| `POST` | `/api/ai/root-cause` | Ask AI to summarise the diff between scans |
| `POST` | `/api/ai/chat` | "Ask your site" chatbot turn |

### 4.2.2 The `/api/scan` endpoint

This is the central endpoint. It accepts a JSON body of the form

```json
{
  "url": "https://example.com",
  "max_pages": 50,
  "max_depth": 2,
  "timeout": 10,
  "polite_delay": 0.1,
  "save": true
}
```

The endpoint validates the URL, runs the full pipeline (crawl, analyse,
score), optionally persists the result, and returns a JSON
representation of the `ScanResult` that includes the global score, the
grade, per-category sub-scores, all pages with their status code and
response time, and all issues with their severity, category, type,
description, recommendation and source URL.

A failed crawl never raises an HTTP 500; the endpoint always returns
the partial result it managed to build, with a `warnings` field that
the frontend renders as an inline banner.

### 4.2.3 The `/api/ai/*` endpoints

The three AI endpoints differ in scope.

`POST /api/ai/fix` takes a single `Issue` and returns a structured AI
response with four fields: `simple_explanation`, `why_it_matters`,
`suggested_fix`, `code_snippet`. The JSON schema is enforced via a
prompt template (Section 4.6.3).

`POST /api/ai/root-cause` takes two scan IDs (or a `ScanDiff` payload)
and returns an AI summary describing what likely changed between them
(e.g., "all five new broken links share the `/blog/` folder, which
suggests a problem with the blog template deployment").

`POST /api/ai/chat` takes a free-form question and a conversation
history and returns a Gemini-generated answer grounded in the current
scan's facts. The system prompt is injected by the backend so the
user cannot override the context.

All three endpoints degrade gracefully when no `GEMINI_API_KEY` is
configured: each returns a deterministic fallback response so the
frontend continues to render.

### 4.2.4 Serialisation

All API responses are produced by a single layer (`api/serializers.py`)
that converts the internal dataclasses (`Issue`, `PageResult`,
`ScoreResult`, `ScanResult`, `ScanDiff`) into JSON-friendly
dictionaries. The serialiser is the only place that knows about the
HTTP wire format; the dataclasses themselves remain pure Python.

## 4.3 Backend

The backend is the Python half of the system. It is organised into the
six domain packages introduced in Section 4.1.2. This section
describes each package in the order they participate in a scan.

### 4.3.1 The `crawler/` Package

`crawler/crawler.py` implements `crawl_site(root_url, max_pages,
max_depth, timeout, polite_delay)`, which performs a breadth-first
search over the same-domain internal pages of a website. The crawler
maintains a visited set and a queue, fetches pages concurrently with
a `ThreadPoolExecutor` (network I/O is the bottleneck), respects the
configured page and depth limits, and honours `robots.txt` via Python's
standard `urllib.robotparser`. A per-thread `polite_delay` adds a
configurable sleep between requests to avoid stressing the target
server.

`crawler/url_utils.py` contains the small but consequential URL
helpers. `normalize_url` collapses common syntactic variants into a
canonical form: it lowercases the scheme and host, strips fragments,
removes trailing slashes (so that the root is `http://x`, not
`http://x/`), and folds default index filenames (`index.html`,
`default.html`) into the parent folder. This single function is the
reason the crawler does not visit "/" and "/index.html" twice.
`is_internal_url`, `should_skip_url`, `extract_links` and
`filter_internal_links` complete the package; each is pure and
exhaustively unit-tested.

The crawler returns a `list[PageResult]`. Each `PageResult` carries
the URL, the HTTP status code, the response time in seconds, the
parsed HTML body (or `None` for non-HTML content), the outgoing link
list, an optional error message, the response size in bytes, the
Content-Type header, the full headers dictionary (kept transiently in
memory for the analyser, not persisted), the list of `Set-Cookie`
headers, and a `was_redirected` / `final_url` pair used by the
transport-security analyser.

### 4.3.2 The `analyzer/` Package

The analyser package contains nine independent detectors. Each
detector is a pure function from a list of `PageResult` objects to a
list of `Issue` objects. They share no state. The package-level
`analyze_pages(pages)` function simply calls each detector in turn
and concatenates the results.

| Module | Category | Issues detected |
| --- | --- | --- |
| `seo_analyzer.py` | SEO | Missing title, missing H1, missing meta description, image alt text, broken links, slow response, server error |
| `accessibility.py` | Accessibility | Missing lang, missing viewport, form inputs without labels, generic link text, skipped heading levels, button/link without accessible text, low inline contrast |
| `performance.py` | Performance | Slow response, large page size, excessive HTTP resources, render-blocking scripts, excessive inline CSS, too many inline event handlers |
| `security.py` | Transport Security / Security Headers / Cookies / Info Disclosure | HTTPS use, HSTS, mixed content, CSP, X-Frame-Options, Referrer-Policy, Permissions-Policy, cookies missing Secure/HttpOnly/SameSite, server-version disclosure, target=_blank without `rel=noopener` |
| `tls.py` | Transport Security | Certificate expiry, weak TLS version, self-signed cert, hostname mismatch |
| `schema_org.py` | Schema | Missing JSON-LD, invalid JSON, missing `@context`/`@type`, recommended schema absent for page type |
| `privacy.py` | Privacy | Known third-party trackers (Google Analytics, Meta Pixel, Hotjar, DoubleClick, and a curated list of 18 more) |
| `exposed_paths.py` | Info Disclosure | Probing for sensitive paths such as `.env`, `.git/config`, `wp-admin`, `phpinfo.php` |
| `scoring.py` | (not an analyser) | Computes the global and per-category scores from the issue list |

Each analyser uses the same `Issue` constructor and the same three
severity levels (High, Medium, Low). The scoring engine
(`scoring.py`) walks the combined issue list once, applying weights
of −10 / −5 / −2 to High / Medium / Low respectively starting from a
base of 100, clamping the result to the inclusive range [0, 100], and
mapping the result to one of four grade bands (Excellent ≥ 90, Good
≥ 75, Needs Improvement ≥ 50, Critical otherwise). The same formula
is applied per category, producing the per-category sub-scores
displayed on the dashboard.

### 4.3.3 The `database/` Package

The database package provides an in-process DAO over SQLite. The
schema (`database/schema.sql`) defines four tables — `scans`, `pages`,
`issues`, and `category_scores` — with `ON DELETE CASCADE` foreign
keys so that deleting a scan cleans up all dependent rows. Indices
are placed on `(root_url, scanned_at DESC)` for the History screen,
on `scan_id` for fast page and issue retrieval, and on
`(scan_id, issue_type, url)` for the diff computation.

`database/db.py` provides six functions:

- `init_db()` creates the tables if they do not exist. It is
  idempotent and safe to call at every startup.
- `save_scan(scan)` persists a complete `ScanResult` in a single
  transaction so a partial save is impossible.
- `list_scans(root_url=None, limit=100)` returns lightweight
  `ScanSummary` objects sorted newest-first, with an optional URL
  filter for the History screen.
- `get_scan(scan_id)` reconstructs a full `ScanResult` from disk.
  The raw HTML body is not persisted, so reconstructed scans cannot
  re-run analysers; this trade-off was chosen to keep the database
  small.
- `delete_scan(scan_id)` removes a saved scan; cascade deletion
  handles the dependent rows.
- `get_diff(from_scan_id, to_scan_id)` computes a `ScanDiff` that
  partitions the two scans' issues into "fixed", "new" and
  "unchanged" sets. Two issues are considered the same if their
  `(url, issue_type)` tuple matches; description and severity
  differences are ignored to keep the diff stable across rule
  changes.

### 4.3.4 The `ai/` Package

The `ai/` package contains three Gemini-backed assistants and a shared
prompt library. All three accept inputs that have already been
classified by the rule-based analyser; none of them invents an issue.

- `ai_assistant.py` exposes `generate_ai_fix(issue, page)`. The
  function builds a prompt that includes the issue's URL, type,
  severity, description and recommendation, plus an extracted page
  context (current title, H1, meta description). Gemini is asked to
  return JSON matching a strict four-field schema; the response is
  parsed defensively (Gemini sometimes wraps JSON in code fences) and
  validated. Failure falls back to a deterministic answer derived
  from the analyser's own recommendation.
- `root_cause.py` exposes `analyze_diff(scan_diff)`. It first
  produces a structural summary of the diff — score delta, clusters
  by URL folder, clusters by category — and then asks Gemini to
  describe what most likely changed in the codebase or deployment
  that produced the observed pattern.
- `chatbot.py` exposes `answer(question, history, scan)`. It builds
  a system context from the current scan (score, top issues,
  per-category sub-scores) and recent history, threads the question
  through the Gemini conversation API, and returns the model's
  reply. Conversation memory is implemented on the frontend and
  passed back on every turn.

All three modules share the same fallback behaviour and the same
per-session call cap (configurable via `AI_MAX_CALLS_PER_SESSION`),
so the user cannot accidentally exhaust the free-tier quota.

### 4.3.5 The `reports/` Package

`csv_exporter.py` produces two CSV files: `issues.csv`, with one row
per detected issue, and `pages.csv`, with one row per crawled URL.
`pdf_exporter.py` produces a print-ready PDF using ReportLab. The
PDF contains the scan's metadata, the global health score in large
type with its grade colour, four summary cards (pages, issues, broken
links, average response time), a severity breakdown, and a
multi-page issues table colour-coded by severity. The PDF header
repeats on every page so the table flows naturally across pages.

All exporters take the same `ScanResult` input that the UI consumes,
which means there is only one representation of a scan in the system.

### 4.3.6 The `api/` Package

`api/main.py` defines the FastAPI application with CORS enabled for
the Vite dev server (`http://localhost:5173`). Each endpoint is a
thin function that deserialises its input, calls one of the domain
modules, and serialises the result via `api/serializers.py`. The API
package contains no business logic of its own.

## 4.4 Frontend

The frontend is a React 18 single-page application served by Vite. It
is deliberately small (about 2,750 lines of JavaScript) and depends
only on `react`, `react-dom`, `react-router-dom` and `recharts`.
There is no UI component library; styles live in `src/styles/` and
are written by hand so that every visual element on the screen can be
explained.

### 4.4.1 Application Shell

`App.jsx` is the top-level component. It mounts a router with one
route per screen and renders the persistent `Sidebar` (navigation,
brand) and the screen content beside it. State that needs to be
shared across screens — the most recent scan, the conversation
history, and the user settings — lives in `src/state/`, a lightweight
custom store that uses React's `useSyncExternalStore` so any screen
can subscribe without prop-drilling.

`src/api.js` is the single place that knows about the backend's URL
and the network protocol. Every screen and component imports the
typed wrappers from this file (`api.scan({...})`, `api.listScans()`,
`api.getDiff(...)`, `api.askFix(issue)`, `api.askRootCause(diff)`,
`api.askChat(question, history)`) and never constructs `fetch` calls
of its own. This means that re-pointing the frontend at a remote
backend, were that ever needed, would require editing exactly one
file.

### 4.4.2 Screens

The nine screens correspond directly to the user-facing capabilities
of the platform:

| Screen | File | Purpose |
| --- | --- | --- |
| Landing | `Landing.jsx` | Full-bleed marketing landing page (no sidebar) |
| Overview | `Overview.jsx` | Welcome / "what is SitePulse AI" page |
| Scan | `Scan.jsx` | URL input, options form, run button, post-scan dashboard |
| Issues | `Issues.jsx` | Filterable table of all detected issues |
| Reports | `Reports.jsx` | Buttons to download CSV / PDF for the active scan |
| History | `History.jsx` | List of saved scans, trend chart, diff selector |
| Chat | `Chat.jsx` | Conversational interface to the chatbot |
| Settings | `Settings.jsx` | API key status, model selection, session limit |
| Placeholder | `Placeholder.jsx` | Used as a fall-through for unknown routes |

### 4.4.3 Components

Five core reusable components carry the visual identity of the application:

- `Sidebar.jsx` is the persistent left rail. It contains the
  `Logo` and a navigation list with one row per screen.
- `PageHeader.jsx` renders the screen title, an optional subtitle,
  and an action slot for screen-specific buttons.
- `ScoreGauge.jsx` is the central visual element: a circular SVG gauge
  that animates from zero to the current score, colour-coded by the
  grade band.
- `AiFixDrawer.jsx` is the right-hand drawer that opens when the user
  asks "Ask AI" on an issue. It calls `POST /api/ai/fix` and renders
  the four structured sections.
- `Logo.jsx` is the SitePulse AI wordmark used in the sidebar and on
  exported reports.

Alongside these, a handful of smaller presentational helpers
(`PulseLine`, `HeroLockup`, `Icons`, `NavIcons`) provide the animated
pulse motif, the landing-page hero artwork, and the inline SVG icon
sets used across the navigation and screens.

## 4.5 Graphical User Interface

The user interface follows a single visual language: a calm
indigo / off-white palette with a single emphatic green ("Afeka
green") that is reserved for actionable controls and the "Excellent"
grade band. Severities are colour-coded consistently throughout the
app — red for High, amber for Medium, blue for Low — so that the
same colour means the same thing in the sidebar badge, the issues
table, the per-category bars, and the exported PDF.

The home of the running session is the **Scan screen**. The user
enters a URL, optionally adjusts the four advanced options (max pages,
depth, timeout, polite delay), clicks "Run scan" and watches a small
progress strip while the backend works. Once the scan finishes the
screen pivots to the post-scan dashboard: four summary cards at the
top (pages scanned, issues found, broken links, average response
time), the circular `ScoreGauge` showing the global 0–100 score and
the grade label, a colour bar showing per-category sub-scores, and a
collapsible table of every issue grouped by category and ordered by
severity.

The **Issues screen** is the same table without the dashboard chrome,
plus two filter controls — severity (multi-select) and category
(multi-select) — and a free-text search box. Each row has an "Ask
AI" button that opens the `AiFixDrawer`.

The **History screen** lists every saved scan with its score and
grade, draws a trend chart of score over time using Recharts, and lets
the user pick any two scans to diff. The diff view shows three
columns — fixed, new, unchanged — each rendered as a count and an
expandable list. From this screen the user can also trigger the
root-cause endpoint to obtain an AI-generated explanation of the
diff.

The **Reports screen** offers three download buttons (Issues CSV,
Pages CSV, Report PDF) backed by the corresponding API endpoints.
The **Chat screen** is a familiar conversational layout with the
user's question on the right and the assistant's response on the
left, anchored to the most recent scan so questions like "what should
I fix first?" produce grounded answers.

## 4.6 Algorithms

This section describes the four algorithmic kernels of the system in
enough detail that the reader could reimplement each one. They are
covered in the order they execute during a scan.

### 4.6.1 BFS Crawl with URL Canonicalisation

The crawler implements a textbook breadth-first search with three
modifications. First, the frontier is processed level by level so
that `max_depth` is enforced exactly, rather than as a soft hint.
Second, fetches at each depth level are dispatched to a
`ThreadPoolExecutor`, which gives a roughly N× speed-up for network
I/O (the bottleneck) at the cost of negligible CPU. Third — and most
importantly — every URL discovered on a page is fed through
`normalize_url` before being added to the visited set, which is the
mechanism by which the crawler avoids visiting the same logical page
through three syntactic variants.

`normalize_url` performs five operations in sequence: it lowercases
the scheme and the host; drops the URL fragment; collapses default
index filenames (`index.html`, `default.html`, `index.htm`) into the
parent folder; strips a trailing slash from non-root paths; and
reassembles the URL via `urlunparse`. The query string is preserved
because it is semantically meaningful (a "search" page with different
queries is genuinely a different page).

### 4.6.2 Rule-Based Issue Detection

Every analyser is implemented as a collection of small private
`_check_*` functions. Each function takes a `PageResult` and possibly
a parsed `BeautifulSoup` document, and returns zero or more `Issue`
objects. The public `analyze_pages(pages)` function iterates over
pages, parses HTML once per page (an optimisation that matters at
scale), and dispatches to every check.

This shape — a small pure function per rule — has two virtues. First,
each rule is independently unit-testable; the test suite contains a
dedicated test class per rule, each driven by a minimal in-memory
HTML string. Second, adding a new rule is a strictly local
modification: a single new function plus a single new test class.
Five of the nine analysers were added in this fashion after the
prototype was complete.

### 4.6.3 Health Score and Per-Category Sub-Scores

Once the analysers have run, `analyzer/scoring.py` walks the combined
issue list. It counts the number of High, Medium and Low issues,
subtracts `10 × high + 5 × medium + 2 × low` from a base of 100,
clamps the result to `[0, 100]`, and maps the score to a grade band:
Excellent (≥ 90), Good (≥ 75), Needs Improvement (≥ 50), Critical
otherwise. The same formula is then re-applied per category — once
for each of `SEO`, `Accessibility`, `Performance`, `Security`,
`Schema` — producing the per-category sub-scores that the dashboard
displays as horizontal bars.

The choice of a linear, weighted formula over a learned model is
deliberate. A neural network might produce more nuanced scores, but
no one would be able to explain why a given site lost three points
rather than five. The current formula maps every lost point to a
single rule firing, which is the property that makes the dashboard
defensible.

### 4.6.4 The Gemini Fix Prompt

The AI Fix endpoint is built around a structured prompt template
(`ai/prompts.py`). The template fills in the issue's type, severity,
description, recommendation, the page's URL, and a small page context
(current title, H1, meta description). It instructs the model to
respond as a domain expert speaking to a non-technical site owner
and to return a JSON object with exactly four fields:
`simple_explanation`, `why_it_matters`, `suggested_fix`,
`code_snippet`.

The response is parsed defensively because Gemini occasionally wraps
JSON in markdown code fences. The parser extracts the outermost
balanced object, validates that all four keys are present, and falls
back to a deterministic response if either step fails. The fallback
always uses the analyser's own description and recommendation, so the
user always sees a usable answer.

### 4.6.5 Scan-to-Scan Diff and Root-Cause Clustering

`database.get_diff(from_id, to_id)` reconstructs both scans, indexes
their issues by the `(url, issue_type)` key, and partitions the union
into three sets: present in old only (fixed), present in new only
(new), and present in both (unchanged). The diff also carries the
score delta so the UI can show "−12 since last scan" at a glance.

`ai/root_cause.py` adds an interpretive layer on top of the structural
diff. Before calling Gemini it produces three signals: the score
delta, the distribution of new issues by top-level URL folder
(`/blog/`, `/admin/`, `/`), and the distribution by category. The
prompt then asks the model to explain the most likely cause of the
observed pattern in plain language; the model's response is
post-processed only to remove any code fences. The fallback, used
when Gemini is unavailable, is a deterministic summary of the same
three signals.

### 4.6.6 Conversational Context Building

`ai/chatbot.py` faces a different problem: how to keep the model
grounded in the user's current data without exceeding the prompt
budget. The solution is a layered context. The system prompt
declares the assistant's role and the rule that all answers must
reference the supplied scan. A "current scan" section is then
constructed from the user's most recent saved scan: the global
score, the per-category sub-scores, the top ten issues by severity,
and a count of how many issues fall in each category. The recent
history (up to three previous scans on the same URL) is summarised
into a single sentence — score deltas only — to give the assistant a
sense of trajectory without flooding the prompt with raw data.

The user's question and the (front-end-managed) conversation history
are then appended in Gemini's expected `user` / `model` role format
and the request is sent. The assistant's reply is returned to the
front end verbatim.

---

# 5. Discussion and Lessons Learned

This chapter steps back from the architecture and the tools and
reflects on what the project actually was, where its complexity
lived, and what we — as engineers — take away from it.

## 5.1 The Idea, Complexity, and Implementation

### 5.1.1 The Idea Behind the Idea

The starting point of SitePulse AI was a small frustration. The
public-facing tools that diagnose technical SEO problems on a
website — Google PageSpeed Insights, Screaming Frog, Lighthouse,
Ahrefs Site Audit — are excellent at telling an expert what is
wrong. They are correspondingly bad at telling a non-expert what
to do. A bakery owner with a Wix site does not benefit from being
told that her page has "no `<meta name="description">` element in
the `<head>` of the document"; she benefits from being told,
in plain words, that her page will look bad on Google and given a
ready-to-paste sentence she can put in.

This gap — between detection and explanation — is the kind of
problem that the most recent generation of language models is
uniquely suited to bridge. Gemini and its peers can rephrase a
technical issue in a way that any reader can understand, in a
tone that is calibrated to that reader, and they can synthesise
fix code on demand. SitePulse AI is built around the conjecture
that the bottleneck in the web-health auditing market is not
detection but communication, and that the latter is now soluble.

### 5.1.2 Where the Complexity Lived

It would be a mistake to think that the bulk of the engineering
work went into the AI. The opposite was true: the AI
integration is small in line-count (roughly 700 lines across the
three modules in `ai/`) and conceptually thin. The complexity
lived in three places that surrounded it.

The first was **categorisation and the per-category scoring
system**. A single global 0–100 score is easy to compute but
nearly useless to act on; a site can have a global score of 65
because its SEO is excellent but its Security is broken. We
therefore needed an issue model with first-class categories, a
scoring engine that computes both global and per-category scores,
a persistence layer that stores all of them, an API surface that
exposes them, and a UI that visualises them. Each individual
component was small, but the consistency required across all of
them was where the work lay.

The second was **graceful degradation**. SitePulse AI must do
something useful when there is no GEMINI_API_KEY, when the Gemini
quota is exhausted, when the target site times out, when the
target server returns 5xx errors, when `robots.txt` is missing,
when a URL produces a redirect chain, when the response is not
HTML, and when the parser encounters malformed HTML. Each of
these cases is handled with a documented fallback so that the
user never sees a stack trace. Writing the fallbacks, deciding
what each one should produce, and testing every branch was a
substantial fraction of the second phase of the project.

The third was **the migration**. Replacing the Streamlit prototype
with a React + Vite frontend and a FastAPI backend, while
preserving every piece of analytical logic, required a strict
separation between presentation and domain code that did not
exist in the prototype. We had to retroactively impose dataclass
boundaries that the prototype had blurred, write a serialisation
layer, define the API surface, and rebuild the full set of UI screens on
top of HTTP rather than Python imports. The migration was
ultimately tractable because the domain modules were re-usable —
but only because we made the architectural commitment to
re-usability before we started moving.

### 5.1.3 What the Implementation Looks Like

In its present form SitePulse AI is roughly **6,300 lines of
production Python** in the backend (`crawler`, `analyzer`,
`models`, `database`, `ai`, `reports`, `api`), **~2,750 lines of
JavaScript/JSX** in the React frontend, **~3,500 lines of test
code** comprising 369 unit tests, **11 audit categories** spanning
SEO, Accessibility, Performance, Security (in four sub-categories),
Schema, Privacy and Information Disclosure, **11 HTTP API
endpoints**, and **9 frontend screens** built on `react` +
`react-router-dom` + `recharts` with hand-written CSS.

The project is held under Git with a commit history that tells the
build story step-by-step. Phase 1 ended with an explicit
"prototype complete" commit; Phase 2 begins with the analyser-suite
and React-frontend commit that retired the Streamlit UI.

## 5.2 Lessons Learned

Six lessons stand out across the project's life. Each is followed
by the concrete event that prompted it.

**Lesson 1. Canonicalise once, at the boundary.** Identity
comparisons on user-controlled strings are unreliable. The
`normalize_url` function (§4.6.1) eliminated an entire class of
duplicate-crawl bugs. Whenever a future component admits arbitrary
strings — URLs, file paths, identifiers — the right move is to
define a canonical form once, upstream, and never reason about
the raw form again.

**Lesson 2. Treat LLM output as untrusted input.** The fact that
Gemini sometimes wraps its JSON output in markdown code fences
caused a sequence of intermittent failures during development.
The defensive parser in `ai/ai_assistant.py` solved them once and
for all. The model is on the other side of a network and a
prompt; its output is not under our control, and the parsing
layer should expect that.

**Lesson 3. Externalise vendor choices.** The choice of LLM
provider, model name, free-tier quota and per-session cap are all
exposed as environment variables. When Google quietly disabled the
free tier for `gemini-2.0-flash` we changed a single line in
`.env`. This pattern — surface every vendor-specific decision as
configuration — is cheap to set up and pays off the first time a
vendor changes its mind.

**Lesson 4. A test suite makes refactoring possible.** The 369
tests are not merely a defence against regressions. They are the
reason the migration from Streamlit to React + FastAPI was viable
at all. Without them, every change to a domain module would have
been an act of faith.

**Lesson 5. A reproducible test environment is a force multiplier.**
The bundled test site (`sample_sites/test_site/`) with intentional
bugs in every audit category meant that every new analyser could be
exercised end-to-end without an Internet connection. Adding a new
audit category began with adding a new bug to the test site, not
with finding a real site that exhibited the issue.

**Lesson 6. Dataclasses at every boundary are insurance against
future churn.** The same `Issue` object that an analyser creates is
the same one the database persists and the AI consumes. There is
no second internal representation. This single discipline made the
Streamlit-to-React migration a presentation-tier exercise instead
of a system-wide one.

---

# 6. Summary and Conclusions

## 6.1 Project Summary

SitePulse AI is a Web Health diagnostic platform built as a
two-phase BSc Computer Science final project. It crawls a website,
classifies the issues it finds across five user-facing categories
(SEO, Accessibility, Performance, Security, Schema), uses Google
Gemini to explain each issue in plain language and to propose a
ready-to-paste fix, persists every scan to a local SQLite database
to enable scan-to-scan diffing and root-cause analysis, and exposes
all of this through a FastAPI backend consumed by a React + Vite
single-page application.

The system satisfies every functional and non-functional
requirement of the original engineering document and substantially
exceeds its scope. Where the original document specified a
single-category SEO scanner with a Streamlit user interface, the
final product is a multi-category Web Health platform with three
distinct AI assistants (fix, root-cause, chatbot) on a production
React + FastAPI stack. The architectural separation of detection
from explanation — rule-based analysers decide what counts as a
problem, the AI is restricted to natural-language explanation —
makes the system predictable, testable and defensible. The
codebase is 6,300 lines of production Python plus ~2,750 lines of
JavaScript, covered by 369 unit tests that run in well under a
second.

The most important pieces of evidence that the project meets its
goals are practical. A scan against the bundled 11-page test site
returns a categorised list of seeded issues with non-trivial
per-category sub-scores, a defensible global grade, a downloadable
CSV and PDF, and, with a valid `GEMINI_API_KEY`, an AI-generated
fix snippet for any issue selected. The same pipeline applied to
a real public site produces a comparable report in under a minute.

## 6.2 Future Development

The architecture leaves several natural extensions open. The
ordering below reflects our judgement of impact-per-effort rather
than chronology.

**Real-browser end-to-end tests.** Adding a Playwright test that
drives the React UI through a full scan flow would extend the
existing test discipline to the presentation tier. The test
infrastructure is already aligned with this: the bundled test site
gives a deterministic target and the API already returns
well-typed payloads.

**Computer-vision auditing of images.** With Gemini Vision the
analyser could process every image discovered during the crawl
and (a) propose alt-text automatically rather than only flagging
its absence, and (b) detect off-topic images by comparing their
content to the page's textual context. This would convert
"missing alt" from a diagnostic into a one-click fix.

**Persistent multi-user deployment.** The system was deliberately
built for a single user on a single machine. Adding optional
authentication, multi-tenant data partitioning and a hosted
deployment story would let agencies use SitePulse AI to manage
many client sites side-by-side. The repository pattern in
`database/db.py` keeps this within reach.

**Scheduled scans.** A long-lived process that scans a configured
list of URLs on a cron-like schedule and writes their results to
the database would convert SitePulse AI from an on-demand tool
into a monitoring tool. Combined with the existing root-cause
analysis it would give the user a daily diff summary by email.

**Auto-fix of HTML.** The fix snippets that the AI currently
produces are display-only. A future version could take the
original HTML, apply each accepted fix to the DOM, and emit a
modified file. This is the natural next step after a user has
read the AI's explanation and decided they trust the proposed
change.

**Internationalisation.** The current UI is English-only. The
underlying analysers are language-agnostic, so a Hebrew or other
locale would be a localisation exercise on the presentation tier
only. The Gemini prompts would need a per-locale tone calibration
to feel right in each language.

---

# 7. References

The references below are grouped by topic. Each entry that is
implemented in code is followed by the module that consumes it.

## 7.1 Standards and Specifications

[1] Internet Engineering Task Force, "RFC 7231 — Hypertext Transfer
Protocol (HTTP/1.1): Semantics and Content", June 2014.
*Used in `crawler/crawler.py` for status-code classification (2xx, 3xx,
4xx, 5xx) and in `analyzer/seo_analyzer.py` for broken-link and
server-error detection.*

[2] Internet Engineering Task Force, "RFC 9110 — HTTP Semantics", June
2022. *Used as the modern reference for HTTP semantics, including the
`Content-Length`, `Content-Type` and `Set-Cookie` response headers
consumed by `analyzer/performance.py` and `analyzer/security.py`.*

[3] Internet Engineering Task Force, "RFC 6797 — HTTP Strict Transport
Security (HSTS)", November 2012. *Implemented in
`analyzer/security.py` as the HSTS header check.*

[4] Internet Engineering Task Force, "RFC 6265 — HTTP State Management
Mechanism (cookies)", April 2011. *Used by the cookie analyser in
`analyzer/security.py` for the `Secure`, `HttpOnly` and `SameSite`
attribute checks.*

[5] Internet Engineering Task Force, "RFC 9309 — Robots Exclusion
Protocol", September 2022. *Implemented in `crawler/crawler.py`
through Python's standard `urllib.robotparser`.*

[6] Internet Engineering Task Force, "RFC 8446 — The Transport Layer
Security (TLS) Protocol Version 1.3", August 2018. *Referenced by
`analyzer/tls.py` for TLS version detection.*

## 7.2 Web Standards

[7] World Wide Web Consortium (W3C), "Web Content Accessibility
Guidelines (WCAG) 2.1", Recommendation, June 2018.
https://www.w3.org/TR/WCAG21/. *The accessibility rules in
`analyzer/accessibility.py` (missing language, viewport,
labels, link text, heading order, button text, contrast) follow the
WCAG 2.1 A and AA criteria.*

[8] World Wide Web Consortium (W3C), "Accessible Rich Internet
Applications (WAI-ARIA) 1.2", Recommendation, June 2023.
https://www.w3.org/TR/wai-aria-1.2/. *Used to determine when
`aria-label` and `aria-labelledby` satisfy a label requirement
in `analyzer/accessibility.py`.*

[9] WHATWG, "HTML Living Standard", continuously updated.
https://html.spec.whatwg.org/. *Reference for the meaning of every
HTML element parsed by the analysers.*

[10] schema.org, "schema.org Vocabulary", continuously updated.
https://schema.org/. *Used by `analyzer/schema_org.py` to validate
JSON-LD blocks and to recommend missing schema types by URL pattern.*

## 7.3 Web Security

[11] OWASP Foundation, "OWASP Secure Headers Project", continuously
updated. https://owasp.org/www-project-secure-headers/. *The security
header checks in `analyzer/security.py` (Content-Security-Policy,
X-Frame-Options, X-Content-Type-Options, Referrer-Policy,
Permissions-Policy) are derived from this project's recommendations.*

[12] OWASP Foundation, "OWASP Top 10:2021", September 2021.
https://owasp.org/Top10/. *Used to prioritise which security checks
to implement; the information-disclosure and broken-access-control
categories motivated `analyzer/exposed_paths.py`.*

[13] Mozilla, "Mixed Content", MDN Web Docs, continuously updated.
https://developer.mozilla.org/en-US/docs/Web/Security/Mixed_content.
*Used by `analyzer/security.py` for the mixed-content rule.*

[14] Mozilla, "Cross-Origin Opener Policy and `rel='noopener'`",
MDN Web Docs. *Used for the `target="_blank"` without `rel="noopener"`
check in `analyzer/security.py`.*

## 7.4 Search and Performance

[15] Google Developers, "Google Search Central — SEO Starter Guide",
continuously updated. https://developers.google.com/search/docs.
*General reference for the SEO checks in `analyzer/seo_analyzer.py`
(title, meta description, H1, image alt text).*

[16] Google Developers, "Core Web Vitals", continuously updated.
https://web.dev/articles/vitals. *Reference for the performance
thresholds in `analyzer/performance.py` (page weight, render-blocking
resources, response time).*

[17] Google Developers, "Lighthouse — Automated tool for improving the
quality of web pages", continuously updated.
https://developers.google.com/web/tools/lighthouse. *Reference
implementation that informed the choice of which performance checks
to perform from a static crawler.*

## 7.5 Tools and Frameworks

[18] FastAPI, official documentation, https://fastapi.tiangolo.com/.
*Used to build the API layer in `api/main.py`.*

[19] React, official documentation, https://react.dev/. *Used to build
the single-page application in `frontend/`.*

[20] Vite, official documentation, https://vitejs.dev/. *Used as the
build and development server for the frontend.*

[21] Recharts, official documentation, https://recharts.org/. *Used
for the trend charts on the History screen.*

[22] BeautifulSoup, "Beautiful Soup Documentation",
https://www.crummy.com/software/BeautifulSoup/bs4/doc/. *Used for HTML
parsing throughout the analyser package.*

[23] ReportLab, "User Guide",
https://www.reportlab.com/docs/reportlab-userguide.pdf. *Used for the
PDF report exporter in `reports/pdf_exporter.py`.*

[24] SQLite, "About SQLite", https://www.sqlite.org/about.html. *Used
as the persistence engine in `database/db.py`.*

[25] pytest, official documentation, https://docs.pytest.org/. *Used
for the 369-test suite under `tests/`.*

## 7.6 AI and Language Models

[26] Google, "Gemini API documentation", continuously updated.
https://ai.google.dev/gemini-api/docs. *Used by every module in
`ai/` for natural-language explanation, fix synthesis, root-cause
analysis and conversational responses.*

[27] Google, "Generative Language API — Pricing and quotas",
continuously updated. https://ai.google.dev/pricing. *Reference for
the per-session quota guard in `ai/ai_assistant.py`.*

---

# 8. Appendices

The appendices in this chapter collect material that supports the
main text but is too detailed to belong in the body. They are
intended to be read selectively, by the reader who wants to see a
specific piece of evidence.

## 8.A Full Project Structure

The following tree shows every non-trivial directory in the
repository, with file counts where relevant. Build artefacts
(`__pycache__/`, `node_modules/`, `venv/`, `.pytest_cache/`) and
project-private folders (`.git/`, `.idea/`) are omitted.

```
Web Health & SEO Crawler/
├── api/                      3 Python files
│   ├── __init__.py
│   ├── main.py               FastAPI app, 11 endpoints
│   └── serializers.py        Dataclass → JSON
│
├── crawler/                  3 Python files
│   ├── __init__.py
│   ├── crawler.py            BFS, concurrency, robots.txt
│   └── url_utils.py          normalize_url, extract_links, ...
│
├── analyzer/                 10 Python files
│   ├── __init__.py
│   ├── seo_analyzer.py
│   ├── accessibility.py
│   ├── performance.py
│   ├── security.py
│   ├── tls.py
│   ├── exposed_paths.py
│   ├── schema_org.py
│   ├── privacy.py
│   └── scoring.py            Global + per-category scoring
│
├── ai/                       5 Python files
│   ├── __init__.py
│   ├── ai_assistant.py       generate_ai_fix(issue, page)
│   ├── prompts.py            Shared prompt library
│   ├── root_cause.py         analyze_diff(scan_diff)
│   └── chatbot.py            answer(question, history, scan)
│
├── database/                 2 Python files + 1 schema
│   ├── __init__.py
│   ├── db.py                 DAO functions
│   └── schema.sql            4 tables + indices
│
├── reports/                  3 Python files
│   ├── __init__.py
│   ├── csv_exporter.py
│   └── pdf_exporter.py
│
├── models/                   2 Python files
│   ├── __init__.py
│   └── result_models.py      PageResult, Issue, ScoreResult, ...
│
├── tests/                    17 Python files / 369 tests
│   ├── __init__.py
│   ├── test_url_utils.py
│   ├── test_analyzer.py
│   ├── test_accessibility.py
│   ├── test_performance.py
│   ├── test_security.py
│   ├── test_tls.py
│   ├── test_schema.py
│   ├── test_privacy.py
│   ├── test_exposed_paths.py
│   ├── test_scoring.py
│   ├── test_database.py
│   ├── test_serializers.py
│   ├── test_reports.py
│   ├── test_api.py
│   ├── test_chatbot.py
│   └── test_root_cause.py
│
├── frontend/                 24 JSX/JS files
│   └── src/
│       ├── App.jsx
│       ├── main.jsx
│       ├── api.js            Single source of API URLs
│       ├── components/
│       │   ├── Sidebar.jsx
│       │   ├── PageHeader.jsx
│       │   ├── ScoreGauge.jsx
│       │   ├── AiFixDrawer.jsx
│       │   ├── Logo.jsx
│       │   ├── PulseLine.jsx
│       │   ├── HeroLockup.jsx
│       │   ├── Icons.jsx
│       │   └── NavIcons.jsx
│       ├── screens/
│       │   ├── Landing.jsx
│       │   ├── Overview.jsx
│       │   ├── Scan.jsx
│       │   ├── Issues.jsx
│       │   ├── Reports.jsx
│       │   ├── History.jsx
│       │   ├── Chat.jsx
│       │   ├── Settings.jsx
│       │   └── Placeholder.jsx
│       ├── state/
│       │   └── ScanContext.jsx
│       ├── lib/
│       │   ├── categoryMeta.js
│       │   └── humanize.js
│       └── styles/
│           └── theme.css
│
├── sample_sites/             Bundled test site
│   └── test_site/            11 HTML pages with intentional bugs
│
├── project-book/             This document
├── branding/                 Logos, posters
├── pytest.ini
├── conftest.py
├── requirements.txt
├── run_api.sh                Starts FastAPI on :8001
├── run_dev.sh                Starts API + test site + Vite together
└── README.md
```

## 8.B Test Inventory

The table below repeats the test inventory from Section 3.9.1 with
the path to each test file. Total: **369 tests** in 16 files.

| File path | Tests | Subject |
| --- | --- | --- |
| `tests/test_url_utils.py` | 41 | URL normalisation and helpers |
| `tests/test_analyzer.py` | 28 | SEO analyser rules |
| `tests/test_accessibility.py` | 31 | WCAG-style rules |
| `tests/test_performance.py` | 26 | Performance rules |
| `tests/test_security.py` | 55 | Security headers, cookies, transport |
| `tests/test_tls.py` | 20 | TLS certificate handling |
| `tests/test_schema.py` | 24 | JSON-LD validation |
| `tests/test_privacy.py` | 12 | Tracker detection |
| `tests/test_exposed_paths.py` | 9 | Sensitive-path probing |
| `tests/test_scoring.py` | 29 | Score computation |
| `tests/test_database.py` | 28 | DAO round-trips and diffing |
| `tests/test_serializers.py` | 16 | Dataclass-to-JSON serialisation |
| `tests/test_reports.py` | 12 | CSV / PDF export |
| `tests/test_api.py` | 12 | FastAPI endpoints |
| `tests/test_chatbot.py` | 11 | Chatbot context + Gemini |
| `tests/test_root_cause.py` | 15 | Diff clustering + Gemini |

## 8.C API Endpoint Reference

A flat list of every HTTP endpoint exposed by the FastAPI backend.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Liveness probe |
| `POST` | `/api/scan` | Run a new scan; optionally persist |
| `GET` | `/api/scans` | List saved scans (newest first) |
| `GET` | `/api/scans/{scan_id}` | Reconstruct one saved scan |
| `GET` | `/api/diff` | Diff two saved scans |
| `GET` | `/api/scans/{scan_id}/report/issues.csv` | Issues CSV |
| `GET` | `/api/scans/{scan_id}/report/pages.csv` | Pages CSV |
| `GET` | `/api/scans/{scan_id}/report/report.pdf` | PDF report |
| `POST` | `/api/ai/fix` | AI: explain & fix one issue |
| `POST` | `/api/ai/root-cause` | AI: summarise a diff |
| `POST` | `/api/ai/chat` | AI: chat turn grounded in current scan |

## 8.D Severity Weights and Grade Bands

The scoring formula in `analyzer/scoring.py` is reproduced below in
full.

```
score = 100 − (10 × high_count) − (5 × medium_count) − (2 × low_count)
score = clamp(score, 0, 100)

grade = "Excellent"          if score ≥ 90
grade = "Good"               if 75 ≤ score < 90
grade = "Needs Improvement"  if 50 ≤ score < 75
grade = "Critical"           if score < 50
```

The same formula is applied per category to produce the per-category
sub-scores displayed on the dashboard.

## 8.E Sample CSV Output (`issues.csv`)

The structure of the issues CSV produced by
`reports/csv_exporter.py` is illustrated below. The example is a
two-row excerpt from a scan of the bundled test site.

```
URL,Issue Type,Severity,Description,Recommendation,HTTP Status,Response Time (s)
http://localhost:8000/about.html,Missing Title,High,"The page is missing a <title> tag, or the tag is empty. The title is what appears in the browser tab and in Google's search results.","Add a unique, descriptive <title> tag of 50-60 characters that summarizes the page.",200,0.032
http://localhost:8000/pricing.html,Broken Link,High,"This page links to http://localhost:8000/portfolio.html, which returned HTTP 404.","Update or remove the link to http://localhost:8000/portfolio.html. If the destination has moved, link to its new location instead.",200,0.025
```

## 8.F Environment Configuration (`.env.example`)

The system reads its runtime configuration from environment
variables, typically loaded from a `.env` file at the project root
via `python-dotenv`. The example below shows the supported keys.

```
# --- Google Gemini API ---
# Get a free API key at https://aistudio.google.com/app/apikey
GEMINI_API_KEY=your_gemini_api_key_here

# Maximum number of AI calls allowed per session
AI_MAX_CALLS_PER_SESSION=20

# Gemini model name; gemini-flash-latest has a generous free tier
GEMINI_MODEL=gemini-flash-latest
```

## 8.G How to Run the System

Three local processes constitute the running system. The bundled
`run_dev.sh` script starts all three in the background with a
single Ctrl+C teardown.

```
# Once, after cloning
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd frontend && npm install && cd ..

# Start the whole stack
./run_dev.sh
# Opens:
#   FastAPI backend at http://localhost:8001/api/...
#   Test site at      http://localhost:8000
#   React frontend at http://localhost:5173
```

A single run of the test suite, after activating the venv, is:

```
pytest                  # 369 tests, < 1 s
```
