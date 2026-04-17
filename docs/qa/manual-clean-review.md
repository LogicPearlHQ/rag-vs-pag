# Manual Clean Benchmark Review

Date: 2026-04-17

This file records a manual review of the deterministic clean subset. The review checked whether each response evidence span supports a single-label clean gold answer. The review did not inspect RAG, RAG-ChunkLookup, LogicPearl, or OpenAI extractor predictions.

## Summary

| Status | Count |
|---|---:|
| approved_clean | 22 |
| needs_rebucket | 2 |
| wrong_primary | 1 |

Approved clean records: 22
Approved clean dev records: 9
Approved clean test records: 13

## Decisions

| ID | Status | Approved primary | Acceptable | Rationale |
|---:|---|---|---|---|
| 10872 | approved_clean | b8 | b8 | CFPB states responsive supervision records would be withheld in full under 5 U.S.C. 552(b)(8). |
| 10873 | approved_clean | b8 | b8 | CFPB states responsive horizontal review records would be withheld in full under 5 U.S.C. 552(b)(8). |
| 13064 | approved_clean | b6 | b6 | FAA says names in the FOIA log were redacted and withheld under Exemption 6. |
| 14161 | needs_rebucket | b4 | b4 | The response describes a recommendation to an Initial Denial Authority and says a final decision is still pending, so this is not a clean final application of Exemption 4. |
| 21367 | approved_clean | b5 | b5 | DOE identifies responsive documents and withholds information under Exemption 5 with deliberative-process explanation. |
| 26662 | approved_clean | b5 | b5 | NASA states three pages are withheld in full pursuant to FOIA Exemption 5. |
| 29755 | approved_clean | b5 | b5 | DOJ appeal response says information was properly withheld in full under Exemption 5. |
| 33143 | wrong_primary | b5 | b5, b6 | The response cites both Exemption 5 and Exemption 6, with Exemption 5 first. The mechanical primary of b6 is not a defensible single-label clean gold. |
| 62228 | approved_clean | b8 | b8 | FDIC referral response withholds the responsive pages in entirety under Exemption 8. |
| 63644 | approved_clean | b3 | b3 | FinCEN invokes Bank Secrecy Act protections and FOIA Exemption 3 for SAR records. |
| 63648 | approved_clean | b3 | b3 | FinCEN invokes Bank Secrecy Act protections and FOIA Exemption 3 for SAR records. |
| 63656 | approved_clean | b3 | b3 | FinCEN invokes Bank Secrecy Act protections and FOIA Exemption 3 for SAR records. |
| 67193 | approved_clean | b3 | b3 | ATF identifies eTrace/firearms-trace data and states it is exempt under Exemption 3 and a separate statute. |
| 99793 | approved_clean | b7 | b7 | FBI gives a Glomar response tied to a pending investigation and invokes Exemption 7(A). |
| 102565 | approved_clean | b3 | b3 | FinCEN invokes Bank Secrecy Act protections and FOIA Exemption 3 for SAR-related records. |
| 104856 | approved_clean | b3 | b3 | IRS denies third-party return information under Section 6103 and FOIA Exemption 3. |
| 118656 | needs_rebucket | b6 | b6 | The response says USTRANSCOM routinely applies Exemption 6 but may apply additional exemptions; it does not cleanly apply B6 to located responsive records. |
| 119663 | approved_clean | b6 | b6 | FCC says personal identifying information in responsive complaints was redacted under Exemption 6. |
| 126349 | approved_clean | b6 | b6 | NIST email says a responsive document is being partially redacted pursuant to FOIA Exemption B6. |
| 148003 | approved_clean | b6 | b6 | Army AvMC states responsive records contain information exempt under 5 U.S.C. 552(b)(6). |
| 151457 | approved_clean | b6 | b6 | Department of Labor denies access to personal addresses, phone numbers, and personal email addresses under Exemption 6. |
| 156786 | approved_clean | b7 | b7 | FTC gives a Glomar response because confirming records would reveal information exempt under Exemption 7(A). |
| 174870 | approved_clean | b6 | b6 | TVA says personal information in an enclosed responsive record was redacted under Exemption 6. |
| 176440 | approved_clean | b5 | b5 | FCC says one responsive record is withheld in full under Exemption 5 and explains deliberative-process privilege. |
| 182859 | approved_clean | b6 | b6 | DOE says responsive documents are released with Exemption 6 redactions protecting personal privacy. |

## Fairness Notes

- The deterministic clean subset is preserved separately from the manually approved clean subset.
- Manual exclusions are recorded with status and rationale instead of silently deleting cases.
- Approved primary labels and acceptable-label sets are stored in the manual review sidecar.

