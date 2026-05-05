# Detailed Benchmark Analysis

## 1) Key Metrics
- Flat accuracy: **60.00%**
- GraphRAG accuracy: **90.00%**
- Delta accuracy: **30.00%**
- Avg latency delta (Graph-Flat): **-151.4 ms**
- Total cost delta (Graph-Flat): **-0.0034 USD**

## 2) Pairwise Outcome
- Graph wins: **8** questions
- Flat wins: **2** questions
- Both correct: **10** questions
- Both incorrect: **0** questions

## 3) Category Breakdown
- `hard_multihop`: Flat 0.00%, Graph 100.00%, Delta 100.00%
- `multihop_control`: Flat 100.00%, Graph 100.00%, Delta 0.00%
- `robustness_failcase`: Flat 100.00%, Graph 0.00%, Delta -100.00%

## 4) Graph-Win Cases
- `FQ01` Which company partnered with both OpenAI and Anthropic?
- `FQ02` Which company founded in 2013 partnered with Anthropic?
- `FQ03` Which company is based in San Francisco and partnered with Anthropic?
- `FQ04` Which company announced the Data Intelligence Platform and partnered with OpenAI?
- `FQ05` Which company partnered with Alphabet and OpenAI?
- `FQ06` Which company integrated with Google Cloud and partnered with Anthropic?
- `FQ07` Which company expected investment from both Microsoft and Nvidia?
- `FQ08` Which company made a bid to buy Chrome and entered partnership with Cristiano Ronaldo?

## 5) Flat-Win Cases
- `FQ19` Who founded OpenAI?
- `FQ20` In what year was OpenAI founded?

## 6) Reliability Check
- Scoring is deterministic keyword matching with refusal filtering.
- This is stricter than loose keyword scoring, but still not full semantic/path equivalence.
- Expected target distribution in this benchmark:
- `databricks`: 8 questions
- `anthropic`: 3 questions
- `stability`: 3 questions
- `perplexity`: 2 questions
- `nvidia`: 1 questions
- `deepmind`: 1 questions
- `sam altman`: 1 questions
- `2015`: 1 questions
- If one target dominates heavily, results can look overly optimistic.

## 7) Actionable Next Steps
- Add path-level validation using `path_hint` to verify relation chains explicitly.
- Add anti-overfit samples with balanced entities across Anthropic, Nvidia, Stability, Perplexity, OpenAI, Google, Databricks.
- Keep a held-out benchmark file not touched during prompt/retrieval tuning.

## 8) Cost Reality Check
- Benchmark table above reflects **query-time cost only**.
- GraphRAG usually has additional indexing cost (triple extraction + graph build).
- See [cost_audit.md](C:\Users\dangv\Downloads\VinCourse\day19\Day19-GraphRAG\outputs\cost_audit.md):
- Flat total (query + indexing): ~$0.0119
- Graph total (query + indexing, fixed chunking projection): ~$0.0176
