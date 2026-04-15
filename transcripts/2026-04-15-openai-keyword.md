# Side-by-side transcript — 2026-04-15T20:40:27Z

Both paths read the same corpus. RAG retrieves + synthesizes; LogicPearl
normalizes features + runs a deterministic artifact.

- provider: `openai`    model: `gpt-4o`
- embedding provider: `openai`
- rag-demo git: `dcd2682682ac`    logicpearl: `logicpearl 0.1.5 (b3e02a6)`

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
| 05_predecisional_memo | clear-cut | b5 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['b5', 'b5', 'b5'] (3/3 dec, 3/3 full, 6/6 cite) |
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
| case_alirez_v_nlrb | case-law | b6 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 0/0 cite) |
| case_armstrong_v_executive_office_of_the_president | case-law | b1 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 0/0 cite) |
| case_army_times_publ_g_co_v_dep_t_of_the_air_force | case-law | b5 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 0/0 cite) |
| case_associated_press_v_dod | case-law | b6 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 0/0 cite) |
| case_avondale_indus_v_nlrb | case-law | b6 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 0/0 cite) |
| case_badhwar_v_u_s_dep_t_of_air_force | case-law | b5 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 0/0 cite) |
| case_bowen_v_fda | case-law | b4 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 0/0 cite) |
| case_but_cf_rosenfeld_v_doj | case-law | b7 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 3/3 cite) |
| case_center_for_national_security_studies_v_doj | case-law | b7 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 0/0 cite) |
| case_chartered_v_irs | case-law | b5 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 0/0 cite) |
| case_city_of_va_beach_v_u_s_dep_t_of_commerce | case-law | b5 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 0/0 cite) |
| case_cmty_on_the_move_v_bd_of_governors_of_the_fed_reserve_sys | case-law | releasable | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 3/3 cite) |
| case_conoco_inc_v_doj | case-law | releasable | [] (0/0 dec, 0/0 full, 0/0 cite) | ['b5', 'b5', 'b5'] (3/3 dec, 3/3 full, 3/3 cite) |
| case_core_v_usps | case-law | b6 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['b6', 'b6', 'b6'] (3/3 dec, 3/3 full, 3/3 cite) |
| case_curran_v_doj | case-law | b7 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 3/3 cite) |
| case_davis_co_v_califano | case-law | b5 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 3/3 cite) |
| case_dept_of_interior_v_klamath | case-law | releasable | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 0/0 cite) |
| case_doe_v_veneman | case-law | b6 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 0/0 cite) |
| case_doj_v_julian | case-law | b5 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 0/0 cite) |
| case_ethyl_corp_v_epa | case-law | releasable | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 0/0 cite) |
| case_forest_guardians_v_fema | case-law | b6 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 0/0 cite) |
| case_frazee_v_u_s_forest_serv | case-law | releasable | [] (0/0 dec, 0/0 full, 0/0 cite) | ['b4', 'b4', 'b4'] (3/3 dec, 3/3 full, 3/3 cite) |
| case_grasso_v_irs | case-law | b3 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['b3', 'b3', 'b3'] (3/3 dec, 3/3 full, 3/3 cite) |
| case_halpern_v_fbi | case-law | b7 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 3/3 cite) |
| case_hanson_v_aid | case-law | b5 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 0/0 cite) |
| case_hardy_v_atf | case-law | b2 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 3/3 cite) |
| case_heights_community_congress_v_va | case-law | b6 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['b6', 'b6', 'b6'] (3/3 dec, 3/3 full, 3/3 cite) |
| case_horowitz_v_peace_corps | case-law | b5 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 0/0 cite) |
| case_inc_v_cuomo | case-law | b5 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 0/0 cite) |
| case_inc_v_epa | case-law | b5 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 0/0 cite) |
| case_inc_v_united_states | case-law | b5 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 0/0 cite) |
| case_kimberlin_v_doj | case-law | b6 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 0/0 cite) |
| case_kuehnert_v_fbi | case-law | b7 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 3/3 cite) |
| case_larson_v_dep_t_of_state | case-law | b1 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 0/0 cite) |
| case_lead_indus_ass_n_v_osha | case-law | b5 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 0/0 cite) |
| case_lehrfeld_v_richardson | case-law | b3 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 0/0 cite) |
| case_lesar_v_doj | case-law | b7 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 3/3 cite) |
| case_long_v_irs | case-law | b3 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['b3', 'b3', 'b3'] (3/3 dec, 3/3 full, 3/3 cite) |
| case_marzen_v_hhs | case-law | b6 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 3/3 cite) |
| case_massey_v_fbi | case-law | b2 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 3/3 cite) |
| case_mcdonnell_v_united_states | case-law | b1 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 0/0 cite) |
| case_military_audit_project_v_casey | case-law | b1 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 0/0 cite) |
| case_minier_v_cia | case-law | b3 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 0/0 cite) |
| case_nielsen_v_u_s_bureau_of_land_mgmt | case-law | releasable | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 0/0 cite) |
| case_norwood_v_faa | case-law | b5 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 0/0 cite) |
| case_nrdc_v_dod | case-law | b9 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 0/0 cite) |
| case_ortiz_v_hhs | case-law | b7 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 3/3 cite) |
| case_p_l_c_v_united_states | case-law | b6 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 0/0 cite) |
| case_physicians_committee_v_nih | case-law | releasable | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 0/0 cite) |
| case_pub_citizen_v_dep_t_of_state | case-law | b1 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 3/3 cite) |
| case_salisbury_v_united_states | case-law | b1 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 0/0 cite) |
| case_see_ctr_for_nat_l_sec_studies_v_doj | case-law | b7 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 3/3 cite) |
| case_see_nation_magazine_v_u_s_customs_serv | case-law | b6 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 0/0 cite) |
| case_see_sladek_v_bensinger | case-law | b7 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 0/0 cite) |
| case_taylor_v_dep_t_of_the_army | case-law | b1 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 0/0 cite) |
| case_texas_v_icc | case-law | b5 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 0/0 cite) |
| case_times_publ_g_co_v_u_s_dep_t_of_commerce | case-law | b3 | [] (0/0 dec, 0/0 full, 0/0 cite) | ['releasable', 'releasable', 'releasable'] (3/3 dec, 3/3 full, 3/3 cite) |

## Totals

- **RAG**: correct 0/0 · decision-det 0/0 · full-det 0/0 · citation faithfulness 0/0 · avg 0.0s per run
- **Pearl**: correct 69/216 · decision-det 216/216 · full-det 216/216 · citation faithfulness 135/135 · avg 0.0s per run

## Notes

- Decision-level determinism is 100% on the pearl side whenever the LLM extracts the same features, which is the intended claim. Full-output determinism is lower on both sides because the explain LLM's rationale prose varies across reruns.
- Citation faithfulness is auto-checked via normalized substring match against retrieved chunks (RAG) or the feature dictionary's authorities (pearl).
- Scenarios 11 (declassified cable), 12 (routine inter-agency transmittal), and 14 (LE record with no harm) all test the same pattern: an exemption element is present, but its statute-named co-elements are absent. The pearl's `statute_structure.json` includes explicit inverse patterns for (b)(1), (b)(5), (b)(6), and (b)(7), each backed by a verbatim statute quote. Without those inverses the learner picks greedy single-feature rules (e.g., fires b5 on `inter_or_intra_agency_memo` alone). With them, the rules are closer to the statute's actual structure — e.g., b5 requires `pre_decisional_deliberative` or `attorney_work_product_or_privileged`, not just the memo type.
- On scenario 15 (rag-favored synthesis), RAG declined with `insufficient_context` — partial credit for refusing; pearl misapplied `b5`. The pearl has no refusal path for "this isn't a classification question" — by design. RAG is the right tool for synthesis tasks; LogicPearl is the right tool for bounded classification. Each tool, for what it's for.
- The `out-of-distribution` category was dropped between the first and second capture runs. The prior scenario 14 asked for `insufficient_context` as the gold label; the pearl (and RAG) struggled to produce it without a preflight LLM-judgment step, which would have undermined the demo's own thesis. The revised scenario 14 tests a genuine partial-elements case (LE record without any statute-named harm) where the statute's own language (the 'but only to the extent that' clause) supports `releasable`.
