# docs/api_curl_tests.sh

BASE="http://localhost:8000"

echo "=== Health check ==="
curl -s $BASE/health | python -m json.tool

echo ""
echo "=== Upload a document ==="
curl -s -X POST "$BASE/upload" \
  -F "file=@eval_data/sample.pdf" | python -m json.tool

echo ""
echo "=== Check ingestion status ==="
curl -s "$BASE/status/sample.pdf" | python -m json.tool

echo ""
echo "=== List all documents ==="
curl -s "$BASE/documents" | python -m json.tool

echo ""
echo "=== Query (simple) ==="
curl -s -X POST "$BASE/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the final project due date?", "k": 5}' \
  | python -m json.tool

echo ""
echo "=== Query (with doc filter) ==="
curl -s -X POST "$BASE/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the grading criteria?", "doc_id": "sample.pdf", "k": 5}' \
  | python -m json.tool

echo ""
echo "=== Query (complex) ==="
curl -s -X POST "$BASE/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "Compare the feedback and adaptive learning approaches in AI education", "k": 5}' \
  | python -m json.tool

echo ""
echo "=== Streaming query ==="
curl -s -N "$BASE/query/stream?question=What+are+the+three+main+phases+of+DATA+606"

echo ""
echo "=== Delete a document ==="
curl -s -X DELETE "$BASE/documents/sample.pdf" | python -m json.tool