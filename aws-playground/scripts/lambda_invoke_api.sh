#!/usr/bin/env bash
# Invoke the Python Lambda via API Gateway HTTP endpoint.
# Usage: ./lambda_invoke_api.sh <api_gateway_url> [json_payload]

set -euo pipefail

API_URL="${1:-}"
PAYLOAD="${2:-'{\"action\":\"hello\",\"source\":\"api_gateway\"}'}"

if [[ -z "$API_URL" ]]; then
  echo "Usage: $0 <api_gateway_url> [json_payload]"
  echo ""
  echo "Get the URL from Terraform outputs:"
  echo "  cd terraform && terraform output api_gateway_url"
  exit 1
fi

echo "[INFO] Invoking Lambda via API Gateway"
echo "[INFO] URL: $API_URL"
echo "[INFO] Payload: $PAYLOAD"
echo ""

RESPONSE=$(curl -s -w "\n%{http_code}" \
  -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")

HTTP_BODY=$(echo "$RESPONSE" | sed '$d')
HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)

echo "[INFO] HTTP Status: $HTTP_CODE"
echo "[OK] Response:"
echo "$HTTP_BODY" | python3 -m json.tool 2>/dev/null || echo "$HTTP_BODY"
