#!/bin/bash
# Test LINEAR scoring across KPIs
TOKEN=$(curl -s -X POST 'http://127.0.0.1:8006/prcp/api/auth/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'username=admin' --data-urlencode 'password=admin123' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

test_score() {
  local RULE=$1; local VAL=$2; local DESC=$3
  printf '%-50s : ' "$DESC v=$VAL"
  RAW=$(curl -s -X POST 'http://127.0.0.1:8006/prcp/api/kpi/score-calc' \
    -H 'Content-Type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -d "{\"rule_id\": $RULE, \"value\": $VAL}")
  echo "$RAW" | python3 -c '
import sys,json
d=json.load(sys.stdin)
r=d.get("matched_range") or {}
clamp=r.get("clamped") or "-"
print("score=" + str(d.get("score")) + " range=[" + str(r.get("from")) + "->" + str(r.get("to")) + "] clamped=" + str(clamp))
'
}

echo "=== ROE LINEAR (rule_id=6, 2 锚点 8->60, 15->100) ==="
test_score 6 6   "ROE=6"
test_score 6 8   "ROE=8"
test_score 6 11.5 "ROE=11.5"
test_score 6 12  "ROE=12"
test_score 6 15  "ROE=15"
test_score 6 17  "ROE=17"

echo
echo "=== CET1 LINEAR (rule_id=7, 3 锚点 7.5->60, 11->90, 13->100) ==="
test_score 7 6    "CET1=6"
test_score 7 7.5  "CET1=7.5"
test_score 7 9    "CET1=9"
test_score 7 11   "CET1=11"
test_score 7 12   "CET1=12"
test_score 7 13   "CET1=13"
test_score 7 15   "CET1=15"

echo
echo "=== LCR LINEAR (rule_id=8, 3 锚点 100->60, 120->85, 150->100) ==="
test_score 8 90   "LCR=90"
test_score 8 100  "LCR=100"
test_score 8 110  "LCR=110"
test_score 8 120  "LCR=120"
test_score 8 135  "LCR=135"
test_score 8 150  "LCR=150"

echo
echo "=== EVE LINEAR (rule_id=10, 逆向 3 锚点 -200亿->30, -118亿->100, 0->100) ==="
test_score 10 -300000000000  "EVE=-300亿"
test_score 10 -200000000000  "EVE=-200亿"
test_score 10 -150000000000  "EVE=-150亿"
test_score 10 -117903500000  "EVE=-117.9亿（监管线）"
test_score 10 -50000000000   "EVE=-50亿"
test_score 10 0              "EVE=0"

echo
echo "=== NSFR LINEAR (rule_id=9, 2 锚点 100->60, 120->100) ==="
test_score 9 95   "NSFR=95"
test_score 9 100  "NSFR=100"
test_score 9 110  "NSFR=110"
test_score 9 120  "NSFR=120"
test_score 9 130  "NSFR=130"