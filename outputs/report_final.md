# GraphRAG Benchmark Report

| Metric | Flat RAG | GraphRAG | Delta |
|---|---:|---:|---:|
| Accuracy (20 Q) | 60.00% | 90.00% | 30.00% |
| Avg Latency (ms) | 1305.7 | 1154.3 | -151.4 |
| Avg Input Tokens | 2186.2 | 1041.4 | -1144.8 |
| Avg Output Tokens | 22.4 | 22.7 | 0.3 |
| Estimated Cost / 20 Q (USD) | 0.0068 | 0.0034 | -0.0034 |

## Accuracy by Category
| Category | Flat RAG | GraphRAG | Delta |
|---|---:|---:|---:|
| hard_multihop | 0.00% | 100.00% | 100.00% |
| multihop_control | 100.00% | 100.00% | 0.00% |
| robustness_failcase | 100.00% | 0.00% | -100.00% |

## Scoring Protocol (No Mock)
- Deterministic keyword scoring: `expected_keywords` is parsed as AND-of-OR groups.
- Any refusal-style answer (`cannot answer`, `insufficient`, etc.) is scored as incorrect.
- Both Flat RAG and GraphRAG are evaluated with the same scoring logic.

## Failure Modes
- Entity ambiguity in company names.
- Missing relation chains in extraction.
- Hallucination when retrieval context is weak.
