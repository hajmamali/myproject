#!/bin/bash
# alpha_test.sh - Complete Alpha Launch Test Script
# Version: 1.0.0
# Purpose: Verify all alpha functionality before launch

set -e

BASE_URL="${MAHOUN_API_URL:-http://localhost:8000}"
TEST_DIR="./alpha_test_data"
mkdir -p "$TEST_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
pass_test() {
    echo -e "${GREEN}✅ PASS${NC}: $1"
    ((TESTS_PASSED++))
    ((TESTS_RUN++))
}

fail_test() {
    echo -e "${RED}❌ FAIL${NC}: $1"
    echo -e "${RED}   Error: $2${NC}"
    ((TESTS_FAILED++))
    ((TESTS_RUN++))
}

warn_test() {
    echo -e "${YELLOW}⚠️  WARN${NC}: $1"
}

section() {
    echo ""
    echo "========================================="
    echo "$1"
    echo "========================================="
    echo ""
}

# Start testing
section "🚀 MAHOUN Alpha Launch - E2E Test Suite"
echo "Base URL: $BASE_URL"
echo "Test Data Dir: $TEST_DIR"
echo ""

# Test 1: API Connectivity
section "Test 1: API Connectivity"
if curl -s -f "$BASE_URL/health" > /dev/null; then
    pass_test "API is reachable at $BASE_URL"
else
    fail_test "API connectivity" "Cannot reach $BASE_URL/health"
    exit 1
fi

# Test 2: Health Check
section "Test 2: Health Check"
HEALTH_RESPONSE=$(curl -s "$BASE_URL/health")
HEALTH_STATUS=$(echo "$HEALTH_RESPONSE" | jq -r '.status' 2>/dev/null)

if [ "$HEALTH_STATUS" == "healthy" ] || [ "$HEALTH_STATUS" == "ok" ]; then
    pass_test "Health check reports healthy status"
    echo "$HEALTH_RESPONSE" | jq . 2>/dev/null || echo "$HEALTH_RESPONSE"
else
    fail_test "Health check" "Status is '$HEALTH_STATUS', expected 'healthy' or 'ok'"
fi

# Test 3: System Status
section "Test 3: System Status & Alpha Features"
STATUS_RESPONSE=$(curl -s "$BASE_URL/system/status")
MODE=$(echo "$STATUS_RESPONSE" | jq -r '.mode' 2>/dev/null)
ALPHA_REASONING=$(echo "$STATUS_RESPONSE" | jq -r '.alpha_features.reasoning_api_enabled' 2>/dev/null)
ALPHA_AGENTS=$(echo "$STATUS_RESPONSE" | jq -r '.alpha_features.agent_endpoints_enabled' 2>/dev/null)

if [ "$MODE" == "minimal" ] || [ "$MODE" == "dev" ]; then
    pass_test "System mode is '$MODE' (correct for alpha)"
else
    warn_test "System mode is '$MODE' (expected 'minimal' or 'dev')"
fi

if [ "$ALPHA_REASONING" == "false" ]; then
    pass_test "Reasoning API is disabled (correct for alpha)"
else
    fail_test "Security check" "Reasoning API is enabled (should be disabled in alpha)"
fi

if [ "$ALPHA_AGENTS" == "false" ]; then
    pass_test "Agent endpoints are disabled (correct for alpha)"
else
    fail_test "Security check" "Agent endpoints are enabled (should be disabled in alpha)"
fi

echo "$STATUS_RESPONSE" | jq . 2>/dev/null || echo "$STATUS_RESPONSE"

# Test 4: Verify Disabled Endpoints
section "Test 4: Security - Verify Disabled Endpoints"

# Test reasoning API
REASONING_HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST "$BASE_URL/api/v1/reasoning/generate-verdict" \
  -H "Content-Type: application/json" \
  -d '{"question":"test","facts":[]}')

if [ "$REASONING_HTTP_CODE" == "404" ]; then
    pass_test "Reasoning API correctly returns 404 (disabled)"
else
    fail_test "Security - Reasoning API" "Expected 404, got $REASONING_HTTP_CODE"
fi

# Test MAHOUN agent endpoints
AGENT_HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST "$BASE_URL/api/v1/mahoun/ask-contract" \
  -H "Content-Type: application/json" \
  -d '{"query":"test"}')

if [ "$AGENT_HTTP_CODE" == "404" ]; then
    pass_test "Agent endpoints correctly return 404 (disabled)"
else
    fail_test "Security - Agent endpoints" "Expected 404, got $AGENT_HTTP_CODE"
fi

# Test 5: Create Test Documents
section "Test 5: Create Test Documents"
cat > "$TEST_DIR/test_doc_fa.txt" << EOF
این یک سند تست برای سیستم MAHOUN است.
این سند شامل متن فارسی برای آزمایش chunking و embedding می‌باشد.
سیستم باید این متن را به چانک‌های کوچکتر تقسیم کند.
سپس برای هر چانک یک بردار embedding تولید می‌کند.
در نهایت این بردارها در ChromaDB ذخیره می‌شوند.
تست جستجو نیز با استفاده از این متن انجام می‌شود.
EOF

cat > "$TEST_DIR/test_doc_en.txt" << EOF
This is a test document for the MAHOUN system.
The system should chunk this text into smaller pieces.
Then it generates embeddings for each chunk.
Finally, the vectors are stored in ChromaDB.
Search tests will use this document as well.
EOF

pass_test "Created test documents (Persian & English)"

# Test 6: Document Upload (Persian)
section "Test 6: Document Upload (Persian)"
UPLOAD_RESPONSE=$(curl -s -X POST "$BASE_URL/api/ingest/upload" \
  -F "file=@$TEST_DIR/test_doc_fa.txt" \
  -F "doc_type=document")

echo "$UPLOAD_RESPONSE" | jq . 2>/dev/null || echo "$UPLOAD_RESPONSE"

SUCCESS=$(echo "$UPLOAD_RESPONSE" | jq -r '.success' 2>/dev/null)
DOC_ID=$(echo "$UPLOAD_RESPONSE" | jq -r '.document_id' 2>/dev/null)
CHUNKS=$(echo "$UPLOAD_RESPONSE" | jq -r '.chunks_created' 2>/dev/null)
INDEXED=$(echo "$UPLOAD_RESPONSE" | jq -r '.indexed' 2>/dev/null)

if [ "$SUCCESS" == "true" ]; then
    pass_test "Persian document uploaded successfully"
    echo "  Document ID: $DOC_ID"
    echo "  Chunks: $CHUNKS"
    echo "  Indexed: $INDEXED"
    
    if [ "$CHUNKS" -gt 0 ]; then
        pass_test "Chunks created ($CHUNKS chunks)"
    else
        fail_test "Chunking" "No chunks created"
    fi
    
    if [ "$INDEXED" == "true" ]; then
        pass_test "Document indexed successfully"
    else
        fail_test "Indexing" "Document not indexed"
    fi
else
    fail_test "Document upload" "Upload failed or returned error"
fi

# Test 7: Document Upload (English)
section "Test 7: Document Upload (English)"
UPLOAD_EN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/ingest/upload" \
  -F "file=@$TEST_DIR/test_doc_en.txt" \
  -F "doc_type=document")

SUCCESS_EN=$(echo "$UPLOAD_EN_RESPONSE" | jq -r '.success' 2>/dev/null)

if [ "$SUCCESS_EN" == "true" ]; then
    pass_test "English document uploaded successfully"
else
    fail_test "English document upload" "Upload failed"
fi

echo "$UPLOAD_EN_RESPONSE" | jq . 2>/dev/null || echo "$UPLOAD_EN_RESPONSE"

# Test 8: Search Test (after indexing delay)
section "Test 8: Search Functionality"
echo "Waiting 3 seconds for indexing to complete..."
sleep 3

# Search for Persian content
SEARCH_FA_RESPONSE=$(curl -s -X POST "$BASE_URL/v1/search/verdicts" \
  -H "Content-Type: application/json" \
  -d '{"query": "سیستم MAHOUN", "limit": 5}')

echo "$SEARCH_FA_RESPONSE" | jq . 2>/dev/null || echo "$SEARCH_FA_RESPONSE"

SEARCH_SUCCESS=$(echo "$SEARCH_FA_RESPONSE" | jq -r '.success' 2>/dev/null)
RESULT_COUNT=$(echo "$SEARCH_FA_RESPONSE" | jq '.results | length' 2>/dev/null)

if [ "$SEARCH_SUCCESS" == "true" ]; then
    pass_test "Search API responds successfully"
    
    if [ "$RESULT_COUNT" -gt 0 ]; then
        pass_test "Search returned $RESULT_COUNT results"
    else
        warn_test "Search returned no results (may need more indexing time)"
    fi
else
    fail_test "Search functionality" "Search API returned error or no response"
fi

# Test 9: Chunker Configuration
section "Test 9: Chunker Configuration"
CONFIG_RESPONSE=$(curl -s "$BASE_URL/api/ingest/config/chunker")
echo "$CONFIG_RESPONSE" | jq . 2>/dev/null || echo "$CONFIG_RESPONSE"

CHUNK_SIZE=$(echo "$CONFIG_RESPONSE" | jq -r '.chunk_size' 2>/dev/null)

if [ ! -z "$CHUNK_SIZE" ] && [ "$CHUNK_SIZE" != "null" ]; then
    pass_test "Chunker config retrieved successfully"
    echo "  Chunk size: $CHUNK_SIZE"
else
    fail_test "Chunker config" "Failed to retrieve configuration"
fi

# Update config
UPDATE_CONFIG_RESPONSE=$(curl -s -X POST "$BASE_URL/api/ingest/config/chunker" \
  -H "Content-Type: application/json" \
  -d '{"chunk_size": 800, "overlap": 100}')

UPDATED_SIZE=$(echo "$UPDATE_CONFIG_RESPONSE" | jq -r '.chunk_size' 2>/dev/null)

if [ "$UPDATED_SIZE" == "800" ]; then
    pass_test "Chunker config updated successfully"
else
    fail_test "Chunker config update" "Config not updated or invalid response"
fi

# Test 10: Metrics Collection
section "Test 10: Metrics Collection"
METRICS_RESPONSE=$(curl -s "$BASE_URL/metrics/legal")
echo "$METRICS_RESPONSE" | jq '{total_queries, avg_duration_seconds, error_rate}' 2>/dev/null || echo "$METRICS_RESPONSE"

TOTAL_QUERIES=$(echo "$METRICS_RESPONSE" | jq -r '.total_queries' 2>/dev/null)

if [ ! -z "$TOTAL_QUERIES" ] && [ "$TOTAL_QUERIES" != "null" ]; then
    pass_test "Metrics collection working"
    echo "  Total queries: $TOTAL_QUERIES"
else
    fail_test "Metrics collection" "Failed to retrieve metrics"
fi

# Test 11: Prometheus Metrics
PROM_RESPONSE=$(curl -s "$BASE_URL/metrics/prometheus")

if echo "$PROM_RESPONSE" | grep -q "mahoun_"; then
    pass_test "Prometheus metrics endpoint responds"
else
    warn_test "Prometheus metrics may not be properly formatted"
fi

# Test 12: Multiple Document Upload (Light Stress)
section "Test 12: Multiple Document Upload (Stress Test)"
echo "Uploading 5 documents sequentially..."

STRESS_PASS=0
STRESS_FAIL=0

for i in {1..5}; do
  cat > "$TEST_DIR/stress_doc_$i.txt" << EOF
این سند استرس تست شماره $i است.
محتوای تست برای بررسی عملکرد سیستم تحت بار.
سیستم باید بتواند چندین سند را به صورت پی‌درپی پردازش کند.
EOF
  
  STRESS_RESPONSE=$(curl -s -X POST "$BASE_URL/api/ingest/upload" \
    -F "file=@$TEST_DIR/stress_doc_$i.txt" \
    -F "doc_type=document")
  
  STRESS_SUCCESS=$(echo "$STRESS_RESPONSE" | jq -r '.success' 2>/dev/null)
  
  if [ "$STRESS_SUCCESS" == "true" ]; then
    ((STRESS_PASS++))
    echo "  ✅ Document $i/5 uploaded successfully"
  else
    ((STRESS_FAIL++))
    echo "  ❌ Document $i/5 failed"
  fi
done

if [ "$STRESS_PASS" == "5" ]; then
    pass_test "All 5 stress test documents uploaded successfully"
elif [ "$STRESS_PASS" -gt 0 ]; then
    warn_test "$STRESS_PASS/5 documents uploaded ($STRESS_FAIL failed)"
else
    fail_test "Stress test" "All documents failed to upload"
fi

# Final Summary
section "📊 Test Suite Summary"

echo "Tests Run:    $TESTS_RUN"
echo "Tests Passed: $TESTS_PASSED"
echo "Tests Failed: $TESTS_FAILED"
echo ""

if [ "$TESTS_FAILED" -eq 0 ]; then
    echo -e "${GREEN}=========================================${NC}"
    echo -e "${GREEN}🎉 ALL TESTS PASSED!${NC}"
    echo -e "${GREEN}=========================================${NC}"
    echo ""
    echo "Alpha system is ready for frontend integration!"
    echo ""
    echo "Next steps:"
    echo "1. Share API documentation with frontend team"
    echo "2. Configure CORS for frontend domain"
    echo "3. Set up monitoring dashboard"
    echo "4. Begin user acceptance testing"
    EXIT_CODE=0
else
    echo -e "${RED}=========================================${NC}"
    echo -e "${RED}❌ SOME TESTS FAILED${NC}"
    echo -e "${RED}=========================================${NC}"
    echo ""
    echo "Please fix the failing tests before proceeding with launch."
    echo "Review logs and error messages above for details."
    EXIT_CODE=1
fi

# Cleanup
echo ""
echo "Cleaning up test data..."
rm -rf "$TEST_DIR"
echo "Done!"

exit $EXIT_CODE
