.PHONY: fetch index build extract-live adjudicate-live manual-review-clean demo-live demo-clean-approved trace-viewer final-report smoke regression diff-ruleset scrape test clean

.DEFAULT_GOAL := final-report

PYTHON ?= python
OPENAI_MODEL ?= gpt-4o-mini

fetch:
	$(PYTHON) corpus/fetch.py

index: fetch
	$(PYTHON) rag/index.py

build:
	$(PYTHON) pearl/build.py --ruleset pearl/rulesets/v1/rules.json --output pearl/artifact/v1
	$(PYTHON) pearl/build.py --ruleset pearl/rulesets/v2/rules.json --output pearl/artifact/v2

extract-live:
	$(PYTHON) extraction/shared_extractor.py --scenarios scenarios/muckrock_snapshot.100.live.json --output extraction/outputs/shared_features.100.live.openai.json --model $(OPENAI_MODEL) --cache-dir extraction/cache/openai

adjudicate-live:
	$(PYTHON) scripts/adjudicate_benchmark.py --scenarios scenarios/muckrock_snapshot.100.live.json --split scenarios/split.100.live.json --adjudication-output scenarios/adjudication.100.live.json --clean-output scenarios/muckrock_snapshot.100.live.clean.json --clean-split-output scenarios/split.100.live.clean.json --report-output docs/qa/live-benchmark-adjudication.md

manual-review-clean: adjudicate-live
	$(PYTHON) scripts/apply_manual_clean_review.py --scenarios scenarios/muckrock_snapshot.100.live.clean.json --split scenarios/split.100.live.clean.json --review scenarios/manual_review.100.live.clean.json --output scenarios/muckrock_snapshot.100.live.clean.approved.json --split-output scenarios/split.100.live.clean.approved.json --report-output docs/qa/manual-clean-review.md

demo-live: index build extract-live adjudicate-live
	LP_LLM_MODEL=$(OPENAI_MODEL) LP_RAG_MODEL=$(OPENAI_MODEL) LP_RAG_CACHE_DIR=extraction/cache/rag_baselines $(PYTHON) compare.py --scenarios scenarios/muckrock_snapshot.100.live.json --split scenarios/split.100.live.json --shared-features extraction/outputs/shared_features.100.live.openai.json --adjudication scenarios/adjudication.100.live.json --out transcripts/live-100-openai-run.jsonl --summary transcripts/live-100-openai-summary.md --repeats 3

demo-clean-approved: index build extract-live manual-review-clean
	LP_LLM_MODEL=$(OPENAI_MODEL) LP_RAG_MODEL=$(OPENAI_MODEL) LP_RAG_CACHE_DIR=extraction/cache/rag_baselines $(PYTHON) compare.py --scenarios scenarios/muckrock_snapshot.100.live.clean.approved.json --split scenarios/split.100.live.clean.approved.json --shared-features extraction/outputs/shared_features.100.live.openai.json --adjudication scenarios/adjudication.100.live.json --out transcripts/live-100-openai-clean-approved-run.jsonl --summary transcripts/live-100-openai-clean-approved-summary.md --repeats 3

trace-viewer: index build extract-live manual-review-clean
	LP_LLM_MODEL=$(OPENAI_MODEL) LP_RAG_MODEL=$(OPENAI_MODEL) LP_RAG_CACHE_DIR=extraction/cache/rag_baselines $(PYTHON) scripts/make_trace_viewer.py --scenarios scenarios/muckrock_snapshot.100.live.json --shared-features extraction/outputs/shared_features.100.live.openai.json --adjudication scenarios/adjudication.100.live.json --manual-review scenarios/manual_review.100.live.clean.json --output docs/demo/trace-viewer.md --ids 63644 13064

final-report: demo-live demo-clean-approved trace-viewer
	$(PYTHON) scripts/write_final_benchmark_report.py --output docs/qa/final-benchmark-report.md --full-summary transcripts/live-100-openai-summary.md --approved-summary transcripts/live-100-openai-clean-approved-summary.md

smoke: test regression diff-ruleset

regression: build
	$(PYTHON) pearl/regression.py --ruleset pearl/rulesets/v2/rules.json --cases pearl/traces/regression_cases.jsonl

diff-ruleset:
	$(PYTHON) pearl/diff_ruleset.py pearl/rulesets/v1/rules.json pearl/rulesets/v2/rules.json

scrape:
	$(PYTHON) scripts/corpus_build/scrape_muckrock.py --output scenarios/archive/muckrock_snapshot.live.json

test:
	$(PYTHON) -m pytest

clean:
	rm -rf corpus/raw rag/index.json extraction/outputs pearl/artifact transcripts .pytest_cache
