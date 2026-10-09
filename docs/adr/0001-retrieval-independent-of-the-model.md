# 0001: Retrieval depends only on the raw query

Retrieval takes the user's raw query and nothing else. No model rewrites the query, picks sections or expands cross-references. Code builds the evidence packet, and any model only writes narration around it.

**Why:** the claim that Ibid is exact on citations is only testable if the evidence packet is byte-identical across models. A model-driven query rewrite would make retrieval vary by model and hide failures.

**Cost:** weaker handling of vague or conversational queries than a model-rewritten pipeline. Accepted for v1. A rewrite step may return later as an opt-in layer that must beat the baseline on the gold set and report its own packet separately.

**Check:** a model that cites a provision outside the packet is flagged.
