#!/usr/bin/env bash

set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8012}"

echo "== Health check =="

curl -fsS \
  "$BASE_URL/health" |
  python3 -m json.tool

echo
echo "== One paid synthetic-model request =="

curl -fsS \
  -X POST \
  "$BASE_URL/draft" \
  -H 'Content-Type: application/json' \
  -d '{
    "donor_id": "SYN-SMOKE-001",
    "first_name": "Jordan",
    "gift_amount": 75.00,
    "relief_area": "emergency food and clean-water distribution",
    "channel": "email"
  }' |
  python3 -m json.tool
