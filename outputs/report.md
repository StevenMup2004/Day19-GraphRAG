# GraphRAG Benchmark Report

| Metric | Flat RAG | GraphRAG | Delta |
|---|---:|---:|---:|
| Accuracy (20 Q) | 80.00% | 90.00% | 10.00% |
| Avg Latency (ms) | 2218.4 | 1605.0 | -613.5 |
| Avg Input Tokens | 2174.3 | 1198.1 | -976.2 |
| Avg Output Tokens | 26.5 | 21.6 | -4.9 |
| Estimated Cost / 20 Q (USD) | 0.0068 | 0.0039 | -0.0030 |

## Failure Modes
- Entity ambiguity in company names.
- Missing relation chains in extraction.
- Hallucination when retrieval context is weak.
