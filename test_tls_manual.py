"""
test_tls_manual.py
==================

Manual sanity check for the live TLS inspector (NOT a pytest test).

Runs analyzer.tls.inspect_tls against a few real hosts and prints what it
found, so you can confirm the socket/ssl layer actually works against the
real internet — not just the mocked unit tests.

Run:
    python test_tls_manual.py
"""

from __future__ import annotations

from analyzer.tls import inspect_tls

# A mix of hosts that exercise the different outcomes:
HOSTS = [
    ("good — modern TLS, valid cert", "www.google.com"),
    ("good — github", "github.com"),
    ("EXPIRED cert (should fail handshake)", "expired.badssl.com"),
    ("WRONG host cert (should fail handshake)", "wrong.host.badssl.com"),
    ("SELF-SIGNED cert (should fail handshake)", "self-signed.badssl.com"),
    ("OLD TLS 1.0 only", "tls-v1-0.badssl.com"),  # note: uses port 1010
    ("nonexistent host (graceful failure)", "nonexistent.invalid.example.test"),
]


def main() -> None:
    print("\nLive TLS inspection against real hosts\n" + "=" * 60)
    for label, host in HOSTS:
        # badssl's old-TLS hosts listen on a non-443 port.
        port = 1010 if host == "tls-v1-0.badssl.com" else 443
        info = inspect_tls(host, port=port, timeout=8)
        print(f"\n{label}")
        print(f"  host:        {host}:{port}")
        print(f"  handshake:   {'OK' if info.handshake_ok else 'FAILED'}")
        if info.handshake_ok:
            print(f"  TLS version: {info.protocol_version}"
                  f"  ({'OUTDATED' if info.is_outdated_version else 'current'})")
            days = info.days_until_expiry()
            print(f"  cert expiry: {info.cert_not_after}  ({days} days left)")
        else:
            print(f"  reason:      {info.failure_kind}")
            print(f"  error:       {info.error}")
    print("\n" + "=" * 60)
    print("What to expect now that we verify against the certifi CA bundle:")
    print("- google.com / github.com -> handshake OK, TLSv1.3, real expiry date.")
    print("- expired.badssl.com      -> FAILED, reason 'expired'.")
    print("- wrong.host.badssl.com   -> FAILED, reason 'hostname_mismatch'.")
    print("- self-signed.badssl.com  -> FAILED, reason 'self_signed'.")
    print("- tls-v1-0.badssl.com     -> FAILED, reason 'protocol' (old TLS).")
    print("- nonexistent host        -> FAILED, reason 'network' (graceful).")
    print("Each broken case maps to a specific, actionable issue in the scanner.")
    print()


if __name__ == "__main__":
    main()
