# Rule-based cross-reference resolution and chain lookup

Status: done
Blocked by: 02, 03

## What to build
A cross-reference resolver that detects references inside provision text by rule (for example "as defined in section 2(8)", "under sub-section (1)") and resolves each to a citation in the same Act, or records it as unresolved with a reason. The result is the cross-reference graph across both Acts. A citation lookup returns the provision plus the provisions it refers to, so a chain is followed in code. No model decides what refers to what (ADR 0001).

## User stories
7, 8, 10

## Acceptance criteria
- [ ] Through `ibid eval`, a cross-reference-chain item returns the provision and the resolved provisions it points to, in a fixed order.
- [ ] Relative references ("this section", "sub-section (2)") resolve against the containing provision.
- [ ] Each unresolved reference is listed with its source citation, matched text and reason; the run reports resolved and unresolved counts for each Act.
- [ ] Seen failing once: a gold chain item whose target is deliberately wrong scores as a miss.
- [ ] Results stay byte-identical across two runs.
