# Glossary

This benchmark uses a few terms narrowly. They are defined here so the
reported numbers are easier to audit.

## Decision Artifact

The compiled, versioned decision object used by the LogicPearl pipeline. In
this repo it is built from a ruleset and supporting metadata, then used to
turn extracted facts into a verdict.

A decision artifact is not a legal authority and is not an official FOIA
policy. It is the benchmark's executable decision layer.

## Ruleset

The human-readable JSON rules under `pearl/rulesets/`. A ruleset maps
extracted boolean features to one of the benchmark verdicts, such as `b5`,
`b6`, `b7`, or `insufficient_facts`.

Rulesets are versioned so changes can be diffed and regression-tested.

## Trace-Valid

A LogicPearl result is trace-valid when the verdict is acceptable for the
scenario and the decision came from a non-default rule with cited authority
IDs.

This is stricter than ordinary accuracy because it requires the decision to
be inspectable, not merely correct by label.

## Citation Support

Citation support measures whether a pipeline's cited authority actually
supports its own verdict.

For plain RAG, the model writes excerpt text and the benchmark checks whether
that excerpt appears in retrieved corpus text. For RAG-ChunkLookup, the model
returns chunk IDs and the application resolves citation text server-side.
For LogicPearl, authority IDs come from the fired rule.

## Track A

The end-to-end track. Each pipeline receives only the request text and agency
name.

Track A includes extraction quality, retrieval quality, model behavior, and
decision behavior.

## Track B

The shared-facts track. One OpenAI structured extractor produces the feature
vector, and every pipeline receives that same feature vector.

Track B isolates the decision layer. It should not be described as an
end-to-end benchmark.

## Approved-Clean

The manually reviewed subset of mechanically clean cases. A case is included
only when the response evidence supports a defensible single-label gold
answer.

Approved-clean results are useful for auditability, but the held-out test set
is small and should not be overclaimed.

## Acceptable-Label Scoring

An ambiguity-aware score for messy live FOIA responses. Some agency letters
cite overlapping exemptions, so the benchmark records a set of acceptable
labels instead of forcing every case into a single strict label.

Acceptable-label scoring is used for the full live benchmark. Strict scores
are still reported in the final benchmark report.
