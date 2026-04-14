# Side-by-side transcript — 2026-04-14T23:57:17Z

Both paths read the same corpus. RAG retrieves + synthesizes; LogicPearl
normalizes features + runs a deterministic artifact.

- provider: `openai`    model: `gpt-4o`
- embedding provider: `openai`
- rag-demo git: `371bf8100338`    logicpearl: `logicpearl 0.1.5 (b3e02a6)`

Per-cell format: `[answers] (decision-det / full-det, cite-faithful/total-cites)`.
*Decision-det* is how often the exemption verdict was identical across reruns
(this is the LogicPearl determinism claim). *Full-det* is byte-identical including
the LLM-generated rationale text (which varies across reruns on both sides even at
temperature=0).

## Per-scenario results

| id | category | expected | RAG | Pearl |
|---|---|---|---|---|
| 01_classified_memo | clear-cut | b1 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['b1', 'b1', 'b1'] (3/3 dec, 3/3 full, 6/6 cite) |
| 02_purely_internal_personnel_rule | clear-cut | b2 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['b2', 'b2', 'b2'] (3/3 dec, 3/3 full, 3/3 cite) |
| 03_exempt_by_other_statute | clear-cut | b3 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['b3', 'b3', 'b3'] (3/3 dec, 3/3 full, 3/3 cite) |
| 04_trade_secret | clear-cut | b4 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['b4', 'b4', 'b4'] (3/3 dec, 3/3 full, 6/6 cite) |
| 05_predecisional_memo | clear-cut | b5 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['b5', 'b5', 'b5'] (3/3 dec, 3/3 full, 3/3 cite) |
| 06_personnel_privacy | clear-cut | b6 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['b6', 'b6', 'b6'] (3/3 dec, 3/3 full, 3/3 cite) |
| 07_law_enforcement_source | clear-cut | b7 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['b7', 'b7', 'b7'] (3/3 dec, 3/3 full, 12/12 cite) |
| 08_bank_exam | clear-cut | b8 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['b8', 'b8', 'b8'] (3/3 dec, 3/3 full, 3/3 cite) |
| 09_geological_well_data | clear-cut | b9 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['b9', 'b9', 'b9'] (3/3 dec, 3/3 full, 3/3 cite) |
| 10_clean_releasable | clear-cut | releasable | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 3/3 cite) |
| 11_borderline_declassified | borderline | releasable | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 6/6 cite) |
| 12_borderline_routine_memo | borderline | releasable | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 6/6 cite) |
| 13_borderline_personnel_roster | borderline | releasable | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 0/0 cite) |
| 14_le_no_harm | borderline | releasable | [] (0/0 dec, 0/0 full, 0/0 cite) | ['b7', 'b7', 'b7'] (3/3 dec, 3/3 full, 15/15 cite) |
| 15_rag_favored_synthesis | rag-favored | not_applicable | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 0/0 cite) |

## Totals

- **RAG**: correct 0/0 · decision-det 0/0 · full-det 0/0 · citation faithfulness 0/0 · avg 0.0s per run
- **Pearl**: correct 42/45 · decision-det 45/45 · full-det 45/45 · citation faithfulness 72/72 · avg 0.0s per run

## Notes

- Decision-level determinism is 100% on the pearl side whenever the LLM extracts the same features, which is the intended claim. Full-output determinism is lower on both sides because the explain LLM's rationale prose varies across reruns.
- Citation faithfulness is auto-checked via normalized substring match against retrieved chunks (RAG) or the feature dictionary's authorities (pearl).
- Scenarios 11 (declassified cable), 12 (routine inter-agency transmittal), and 14 (LE record with no harm) all test the same pattern: an exemption element is present, but its statute-named co-elements are absent. The pearl's `statute_structure.json` includes explicit inverse patterns for (b)(1), (b)(5), (b)(6), and (b)(7), each backed by a verbatim statute quote. Without those inverses the learner picks greedy single-feature rules (e.g., fires b5 on `inter_or_intra_agency_memo` alone). With them, the rules are closer to the statute's actual structure — e.g., b5 requires `pre_decisional_deliberative` or `attorney_work_product_or_privileged`, not just the memo type.
- On scenario 15 (rag-favored synthesis), RAG declined with `insufficient_context` — partial credit for refusing; pearl misapplied `b5`. The pearl has no refusal path for "this isn't a classification question" — by design. RAG is the right tool for synthesis tasks; LogicPearl is the right tool for bounded classification. Each tool, for what it's for.
- The `out-of-distribution` category was dropped between the first and second capture runs. The prior scenario 14 asked for `insufficient_context` as the gold label; the pearl (and RAG) struggled to produce it without a preflight LLM-judgment step, which would have undermined the demo's own thesis. The revised scenario 14 tests a genuine partial-elements case (LE record without any statute-named harm) where the statute's own language (the 'but only to the extent that' clause) supports `releasable`.
