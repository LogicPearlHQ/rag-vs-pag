# Corpus Build Helpers

These scripts build and inspect MuckRock-derived scenario snapshots:

- `scrape_muckrock.py`: fetch public or authenticated MuckRock data.
- `extract_gold_labels.py`: extract candidate FOIA exemption labels from response text.
- `make_qa_review.py`: create a manual gold-label review worksheet.
- `redact_snapshot.py`: redact saved request/response text.
- `muckrock_client.py`: small API clients used by the scraper.

They are intentionally outside the main benchmark script directory because
the current report path starts from the checked-in scenario snapshots.
