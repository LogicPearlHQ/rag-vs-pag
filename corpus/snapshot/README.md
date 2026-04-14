# Snapshot

Checked-in fallback copies of corpus documents. `corpus/fetch.py` uses a
file here if the canonical URL in `corpus/sources.toml` fails.

The statute (`5_usc_552.txt`) is a plain-text rendering of 5 U.S.C. § 552
extracted from Cornell Legal Information Institute. Federal statutes are
public domain (17 U.S.C. § 105).

This is intended as a minimal offline fallback, not a replacement for the
full corpus. The demo's richer behaviors (DOJ Guide citations, case law
excerpts) require the live fetch.
