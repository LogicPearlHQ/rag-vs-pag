# Corpus Attributions

The demo corpus is fetched by `corpus/fetch.py` from the canonical URLs
declared in `corpus/sources.toml`. All documents are either public domain
federal works or public-domain court opinions redistributed under
CourtListener's terms.

## Federal works (public domain — 17 U.S.C. § 105)

- **5 U.S.C. § 552** — Cornell Legal Information Institute  
  https://www.law.cornell.edu/uscode/text/5/552
- **DOJ Office of Information Policy, *Guide to the Freedom of Information Act*** —  
  https://www.justice.gov/oip/foia-guide
- **28 C.F.R. Part 16** — eCFR  
  https://www.ecfr.gov/current/title-28/chapter-I/part-16

## Court opinions (public domain; text redistributed via CourtListener)

Opinions of U.S. federal courts are public-domain works. The specific
rendering/text we fetch is distributed by the Free Law Project via the
CourtListener API (https://www.courtlistener.com). See CourtListener's
terms for acceptable use; no account is required for the opinion
endpoints used here.

Cases fetched:

- *NLRB v. Sears, Roebuck & Co.*, 421 U.S. 132 (1975)
- *Dep't of State v. Ray*, 502 U.S. 164 (1991)
- *DOJ v. Reporters Committee for Freedom of the Press*, 489 U.S. 749 (1989)
- *FBI v. Abramson*, 456 U.S. 615 (1982)
- *Dep't of the Interior v. Klamath Water Users Protective Ass'n*, 532 U.S. 1 (2001)

## Demo scope disclaimer

The corpus in this repository is a **pedagogical sample** that exercises
the demo pipeline. It is not a substitute for the authoritative source
texts and is not legal advice.
