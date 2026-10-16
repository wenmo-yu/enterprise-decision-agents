# Evidence Review Boundary

`verify_claim_support` is a deterministic report gate, not a general-purpose fact checker. A Markdown report cannot be generated until this tool has run in the current request context.

## What the gate verifies

- each cited `evidence_id` was registered during the current run;
- supplied quotes can be located in the registered evidence snapshot;
- numeric literals in a claim can be found in the cited evidence;
- causal phrasing such as “源于” or “导致” is downgraded to an inference rather than treated as proof;
- declared conflict IDs must also be registered in the current run.

## What the gate does not claim

- It does not independently establish the truth of an external webpage.
- It does not infer contradiction between arbitrary evidence passages. `conflicting` means a caller supplied a valid, registered conflict reference.
- It does not establish causality from coincident operating data and external signals.

This boundary keeps the platform’s evidence claim precise: **claim-level citation completeness and support checks with a formal-report gate**, rather than automatic factual verification or causal discovery.
