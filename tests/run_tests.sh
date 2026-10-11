#!/bin/sh
# End-to-end test: ingest -> audit -> finalize -> immutability -> monitor -> gate -> approve -> guard.
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd); SKILL="$ROOT/skills/ads"; A="$SKILL/scripts/ads.py"; H="$SKILL/hooks"; E="$SKILL/examples/exports"
W=$(mktemp -d); cd "$W"; export ADS_TODAY=2026-10-11 CLAUDE_PROJECT_DIR="$W"
fail=0; ok(){ echo "PASS $1"; }; bad(){ echo "FAIL $1"; fail=1; }
python3 "$A" init --client "Test Co" >/dev/null
python3 - <<PY
import json; p=".ads/client.json"; c=json.load(open(p)); c["accounts"]=["123-456-7890"]
c["targets"]={"default":{"cpa":1200},"google":{"cpa":1100,"roas":3.0},"meta":{"cpa":1300,"roas":2.5}}
c["budgets"]=[{"platform":"google","entity":"*","period":"month","amount":1400000}]; json.dump(c,open(p,"w"))
PY
R=$(python3 "$A" start audit)
python3 "$A" ingest --run "$R" "$E/google_campaigns_daily.csv" "$E/meta_campaigns_sep.csv" "$E/google_search_terms_sep.csv" >/dev/null && ok ingest || bad ingest
OUT=$(python3 "$A" audit --run "$R"); echo "$OUT" | grep -q "TRK003-1" && ok "detects tracking break" || bad "detects tracking break"
echo "$OUT" | grep -q "ST001-1" && ok "detects search term waste" || bad "detects search term waste"
cp "$SKILL/examples/analyst.example.json" ".ads/runs/$R/analyst.json"
python3 "$A" finalize "$R" >/dev/null && ok finalize || bad finalize
python3 "$A" validate ".ads/runs/$R/run.json" >/dev/null && ok "run validates" || bad "run validates"
python3 "$A" finalize "$R" >/dev/null 2>&1 && bad "immutability" || ok "immutability"
test -s ".ads/runs/$R/report.html" && test -s ".ads/runs/$R/report.md" && ok "renders md+html" || bad "renders md+html"
python3 "$A" propose --run "$R" --file "$SKILL/examples/proposal.example.json" > gate.txt && ok "gate passes" || bad "gate passes"
CODE=$(grep -o 'ADS-[0-9A-F]\{6\}' gate.txt | head -1)
TI='{"customer_id":"1234567890","campaign_id":"2233445566","amount_micros":4500000000}'
pre(){ echo "{\"hook_event_name\":\"PreToolUse\",\"cwd\":\"$W\",\"tool_name\":\"$1\",\"tool_input\":$2}" | python3 "$H/guard.py"; }
pre mcp__google-ads-write__update_campaign_budget "$TI" | grep -q deny && ok "blocks unapproved write" || bad "blocks unapproved write"
pre Write '{"file_path":".ads/approvals/x.json"}' | grep -q deny && ok "blocks approval forgery" || bad "blocks approval forgery"
echo "{\"prompt\":\"APPROVE $CODE\",\"cwd\":\"$W\"}" | python3 "$H/approve.py" | grep -q "recorded" && ok "user approval" || bad "user approval"
pre mcp__google-ads-write__update_campaign_budget '{"customer_id":"1234567890","campaign_id":"2233445566","amount_micros":9}' | grep -q deny && ok "blocks altered input" || bad "blocks altered input"
[ -z "$(pre mcp__google-ads-write__update_campaign_budget "$TI")" ] && ok "allows exact approved write" || bad "allows exact approved write"
pre mcp__google-ads-write__update_campaign_budget "$TI" | grep -q deny && ok "blocks replay" || bad "blocks replay"
M=$(python3 "$A" start monitor); python3 "$A" ingest --run "$M" "$E/google_campaigns_daily.csv" >/dev/null; python3 "$A" monitor --run "$M" | grep -q "Pacing" && ok "pacing" || bad "pacing"
echo "workspace: $W"; exit $fail
