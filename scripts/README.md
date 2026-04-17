# Scripts

The top-level scripts are part of the current reproducible benchmark path:

- `adjudicate_benchmark.py`
- `apply_manual_clean_review.py`
- `make_trace_viewer.py`
- `write_final_benchmark_report.py`

Corpus-building and historical QA helpers live in `corpus_build/`. They are
useful for reconstructing the MuckRock snapshot, but `make final-report`
does not call them.
