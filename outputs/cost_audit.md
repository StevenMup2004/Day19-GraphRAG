# Cost Audit (Reality Check)

## 1) Query-Time Cost (from benchmark)
- Flat query cost / 20Q: **$0.0068**
- Graph query cost / 20Q: **$0.0037**
- At query time only, Graph can be cheaper because graph context is shorter.

## 2) Indexing Cost (where GraphRAG is usually more expensive)
- Flat indexing (embedding assumption): **$0.0051**
- Graph indexing (observed old chunking): **$0.0074**
- Graph indexing (projected with fixed chunking): **$0.0138**

## 3) Total Cost View (Query + Indexing)
- Flat total (estimated): **$0.0119**
- Graph total (old chunking): **$0.0112**
- Graph total (fixed chunking projection): **$0.0176**

## 4) Why previous graph cost looked too low
- Old extraction chunking truncated long paragraphs, often to one chunk/article.
- Old extracted chunks: **28**
- New extracted chunks (same max 2/article): **52**
- Old input token estimate: **21260**
- New input token estimate: **39461**

## 5) Conclusion
- If you include indexing, GraphRAG cost moves up substantially.
- For strict apples-to-apples: rerun extraction with fixed chunking, then rerun benchmark.