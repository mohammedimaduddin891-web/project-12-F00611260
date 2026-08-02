#!/usr/bin/env bash
# Project 12 FinOps projection from either the supplied practice bill or a
# normalized real provider cost summary.
#
# Required CSV columns:
#   <tag key selected with --tag-key>, cost_usd
#
# Practice:
# BILL_CSV=sample-bill.csv bash finops_alerts.sh \
#   --budget 500 --threshold 0.8 --tag-key tag --days-elapsed 5
#
# Real bill:
# BILL_CSV=billing/actual-cost-summary.csv bash finops_alerts.sh \
#   --budget 5 --threshold 0.8 --tag-key project --days-elapsed 1

set -euo pipefail

BUDGET="5"
THRESHOLD="0.8"
TAG_KEY="project"
DAYS_ELAPSED="1"
DAYS_IN_MONTH="30"
BILL_CSV="${BILL_CSV:-$(dirname "$0")/sample-bill.csv}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --budget)
      BUDGET="$2"
      shift 2
      ;;
    --threshold)
      THRESHOLD="$2"
      shift 2
      ;;
    --tag-key)
      TAG_KEY="$2"
      shift 2
      ;;
    --days-elapsed)
      DAYS_ELAPSED="$2"
      shift 2
      ;;
    --bill-csv)
      BILL_CSV="$2"
      shift 2
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

[[ -f "$BILL_CSV" ]] || {
  echo "ERROR: billing CSV not found: $BILL_CSV" >&2
  exit 1
}

awk -v n="$BUDGET" \
  'BEGIN {exit !(n+0 == n && n > 0)}' || {
  echo "ERROR: budget must be positive" >&2
  exit 2
}

awk -v n="$THRESHOLD" \
  'BEGIN {exit !(n+0 == n && n > 0 && n <= 1)}' || {
  echo "ERROR: threshold must be greater than zero and no more than one" >&2
  exit 2
}

awk -v n="$DAYS_ELAPSED" \
  'BEGIN {exit !(n+0 == n && n > 0)}' || {
  echo "ERROR: days-elapsed must be positive" >&2
  exit 2
}

fetch_spend_csv() {
  awk -F, -v tag_key="$TAG_KEY" '
    NR == 1 {
      for (i = 1; i <= NF; i++) {
        gsub(/^"|"$/, "", $i)
        header[$i] = i
      }

      tag_col = header[tag_key]
      cost_col = header["cost_usd"]

      if (!tag_col || !cost_col) {
        printf "ERROR: CSV requires columns %s and cost_usd\n",
               tag_key > "/dev/stderr"
        exit 3
      }

      next
    }

    {
      tag = $tag_col
      cost = $cost_col

      gsub(/^"|"$/, "", tag)
      gsub(/^"|"$/, "", cost)

      if (tag != "" && cost != "") {
        sum[tag] += cost
      }
    }

    END {
      for (tag in sum) {
        printf "%s,%.6f\n", tag, sum[tag]
      }
    }
  ' "$BILL_CSV"
}

spend_csv="$(fetch_spend_csv)"

[[ -n "$spend_csv" ]] || {
  echo "ERROR: no spend rows were found" >&2
  exit 1
}

threshold_amount="$(
  awk -v b="$BUDGET" -v t="$THRESHOLD" \
    'BEGIN {printf "%.6f", b*t}'
)"

printf 'FinOps check\n'
printf 'source=%s\n' "$BILL_CSV"
printf 'budget=$%.2f  threshold=%.0f%%  elapsed=%s day(s)  group-by=%s\n' \
  "$BUDGET" \
  "$(awk -v t="$THRESHOLD" 'BEGIN {print t*100}')" \
  "$DAYS_ELAPSED" \
  "$TAG_KEY"

printf '%s\n' \
  '-----------------------------------------------------------------------'

while IFS=, read -r tag observed_cost; do
  projected="$(
    awk \
      -v c="$observed_cost" \
      -v d="$DAYS_ELAPSED" \
      -v m="$DAYS_IN_MONTH" \
      'BEGIN {printf "%.6f", (c/d)*m}'
  )"

  verdict="$(
    awk \
      -v p="$projected" \
      -v limit="$threshold_amount" \
      'BEGIN {print (p >= limit) ? "ALERT" : "ok"}'
  )"

  printf '%-28s observed=$%-10.6f projected=$%-10.6f [%s]\n' \
    "$tag" \
    "$observed_cost" \
    "$projected" \
    "$verdict"

  if [[ "$verdict" == "ALERT" ]]; then
    printf \
      "  >> ALERT: projected spend is at or above %.0f%% of the monthly budget.\n" \
      "$(awk -v t="$THRESHOLD" 'BEGIN {print t*100}')"

    echo \
      "  >> ACTION: inspect request volume, model tier, retries, and idle resources."
  fi
done <<< "$spend_csv"

printf '%s\n' \
  '-----------------------------------------------------------------------'

echo \
  "This script is an alerting control. Provider spend-limit enforcement is separate."
