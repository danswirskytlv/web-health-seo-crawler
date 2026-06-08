# Testing Guide — TLS / Certificate Checks

How to verify the live TLS inspection actually works against real
certificates (not just the mocked unit tests).

The best test is the manual script: it runs the TLS inspector against real
hosts on the internet, including hosts that are deliberately broken, so you
see both a healthy result and a correct failure.

---

## Best test — `test_tls_manual.py`

**1. Activate the environment:**

```bash
cd "/Users/danswir/Documents/Claude/Projects/Web Health & SEO Crawler"
source venv/bin/activate
```

**2. Run the manual TLS check:**

```bash
python test_tls_manual.py
```

**3. What you should see (this is what proves it works):**

- **www.google.com** and **github.com** → `handshake: OK`, version
  `TLSv1.3 (current)`, and a real number of days until the certificate
  expires. → proves the handshake and certificate reading work.
- **expired.badssl.com** → `handshake: FAILED` with a "certificate has
  expired" error. → this is CORRECT: a site with an expired certificate
  *should* fail. Our scanner flags it as "TLS Handshake Failed".
- **wrong.host.badssl.com** and **self-signed.badssl.com** → `FAILED` too,
  as expected.
- **nonexistent.invalid...** → `FAILED` with a DNS error → proves the code
  fails gracefully instead of crashing.

If Google/GitHub succeed (with an expiry date) and the broken hosts fail,
**TLS is fully working.**

> badssl.com is a public service built specifically for testing broken TLS.

---

## Visual test — through the UI

**4. Start the app:**

```bash
streamlit run app.py
```

**5. To see TLS *detect a problem*, scan a deliberately-broken host.**
Enter this URL and scan:

```
https://expired.badssl.com
```

Under the **🔐 Transport Security** category you should see a
**"TLS Handshake Failed"** issue.

**6. For contrast, scan a healthy HTTPS site** (any serious website). No TLS
issues should appear — proving the check doesn't cry wolf when all is well.

---

## Automated tests (already passing)

The mocked unit tests verify all the logic — outdated-version detection,
days-until-expiry math, certificate-date parsing — with no network:

```bash
pytest tests/test_tls.py -v
```

Expected: 12 `PASSED`.

---

## Notes

- On the **local http test site** (`http://localhost:8000`), TLS produces
  nothing — it only runs on real HTTPS hosts, and localhost is skipped on
  purpose (no real certificate). That's expected, not a bug.
- TLS runs only during a live UI scan (`check_tls=True`). The offline analyzer
  and the unit tests never open a socket.
