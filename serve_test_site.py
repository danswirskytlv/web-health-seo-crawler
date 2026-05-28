"""
serve_test_site.py
==================

Local HTTP server for the SEO Crawler test site.

Why this exists
---------------
We need a controlled environment to develop and demo the crawler against —
one that doesn't depend on the public internet and that includes a known set
of SEO bugs (broken links, missing titles, slow pages, server errors, ...).

This server does three things beyond plain static file hosting:

1. /faq.html is intentionally slowed down (3-second delay) to simulate a
   "slow response" issue that the analyzer should flag as Medium severity.

2. /error.html intentionally returns HTTP 500 (server error), so the analyzer
   can detect 5xx status codes.

3. /portfolio.html is referenced from pricing.html but does not exist on disk,
   so the server returns 404 — letting us test broken-link detection.

How to run
----------
    python serve_test_site.py

Then open http://localhost:8000 in your browser or point the crawler at it.

Press Ctrl+C to stop the server.
"""

from __future__ import annotations

import http.server
import socketserver
import time
from pathlib import Path


class ThreadingHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """
    HTTP server that handles each request in its own thread.

    Why this matters: the slow /faq.html (3-second delay) would otherwise
    block all other concurrent requests, making response times look
    artificially high. With threading, /faq.html only slows down /faq.html.
    """
    # daemon_threads = True so Ctrl+C kills outstanding requests immediately
    # instead of waiting for them to finish.
    daemon_threads = True
    allow_reuse_address = True

# --- Configuration --------------------------------------------------------

HOST = "localhost"
PORT = 8000

# Folder containing the HTML files (relative to this script).
SITE_ROOT = Path(__file__).parent / "sample_sites" / "test_site"

# Paths that get special treatment:
SLOW_PATHS = {"/faq.html"}          # served with an artificial delay
ERROR_PATHS = {"/error.html"}        # always return 500
SLOW_DELAY_SECONDS = 3.0


# --- Custom request handler ----------------------------------------------

class TestSiteHandler(http.server.SimpleHTTPRequestHandler):
    """Serves the test site, with intentional slowdowns and errors."""

    def __init__(self, *args, **kwargs):
        # Tell SimpleHTTPRequestHandler to serve files from SITE_ROOT,
        # not from the current working directory.
        super().__init__(*args, directory=str(SITE_ROOT), **kwargs)

    def do_GET(self) -> None:  # noqa: N802 (stdlib naming)
        # Normalize "/" -> "/index.html" so the slow / error checks below work
        # consistently regardless of how the URL was requested.
        path = self.path
        if path in ("", "/"):
            path = "/index.html"

        # Case 1: intentionally slow page.
        if path in SLOW_PATHS:
            print(f"[slow] {path} - delaying {SLOW_DELAY_SECONDS}s")
            time.sleep(SLOW_DELAY_SECONDS)

        # Case 2: intentionally broken server endpoint.
        if path in ERROR_PATHS:
            print(f"[error] {path} - returning 500")
            self.send_error(500, "Intentional server error for testing")
            return

        # Default: let the standard handler serve the file.
        super().do_GET()

    def log_message(self, format: str, *args) -> None:
        # Make server logs a bit more readable in the terminal.
        print(f"[{self.address_string()}] {format % args}")


# --- Entry point ----------------------------------------------------------

def main() -> None:
    if not SITE_ROOT.exists():
        raise SystemExit(
            f"Test site folder not found: {SITE_ROOT}\n"
            "Make sure you're running this script from the project root."
        )

    print("=" * 60)
    print(" Web Health & SEO Crawler - Test Site Server")
    print("=" * 60)
    print(f" Serving:   {SITE_ROOT}")
    print(f" URL:       http://{HOST}:{PORT}")
    print(f" Slow path: {', '.join(SLOW_PATHS)} ({SLOW_DELAY_SECONDS}s delay)")
    print(f" 500 path:  {', '.join(ERROR_PATHS)}")
    print(" Missing:   /portfolio.html (referenced from pricing.html -> 404)")
    print("=" * 60)
    print(" Press Ctrl+C to stop.")
    print()

    # Use the threading-enabled server so concurrent requests don't queue up
    # behind the slow /faq.html endpoint.
    with ThreadingHTTPServer((HOST, PORT), TestSiteHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down test site server. Bye!")


if __name__ == "__main__":
    main()
