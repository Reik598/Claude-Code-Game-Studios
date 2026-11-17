#!/usr/bin/env bash
# frame-stats.sh — the sample statistics /benchmark-report Phase 3 reports for
# one numeric column of a text capture: the sample count, the nearest-rank
# P50, P95 and P99, the max and the mean, and, given a budget, how many samples
# are over it.
#
# Replaces sorting a frame-time column and counting ranks by hand in context,
# which goes wrong on captures of thousands of frames (fix plan AM28 D3).
#
# OBSERVATIONS, NOT A VERDICT (CLAUDE.md, "Helpers in .claude/scripts/"). OK,
# OVER, hitching and the budget verdict stay with /benchmark-report.
#
# READ-ONLY. It reads the capture and writes only to stdout and stderr: no
# file, no temporary file.
#
# Usage: bash .claude/scripts/frame-stats.sh <csv> <column> [budget-ms] [options]
#   <csv>          a text capture: one header line, then one row per sample,
#                  comma-separated (a quoted field holding a comma is not read)
#   <column>       the column's header name, exactly as written, or its
#                  1-based number
#   [budget-ms]    a positive number; adds the budget and over_budget rows
#   --skip N       leave out the first N data rows (warm-up frames the capture
#                  marks; the caller says why)
#   --scale F      multiply every value by F first (0.001 for µs to ms,
#                  0.000001 for ns to ms)
#   -h, --help     this text
#
# Output: TSV, one `key<TAB>value` row each, in this order:
#   file, column, skipped, n, method (nearest-rank), p50, p95, p99, max, mean,
#   and with a budget: budget, over_budget (samples > budget), over_share (%).
# Pk is the value at rank ceil(k × n / 100) of the values in ascending order.
#
# Exit 0 with the rows. Exit 2, with nothing on stdout and the reason on
# stderr, on bad usage (a budget of 0 or less among it), an unreadable file, an
# unknown column, no data row, or a value that is not a number (its line number
# is named). Blank lines are skipped.

set -uo pipefail
export LC_ALL=C

usage() { sed -n '2,/^$/p' "$0" | sed -e 's/^# \{0,1\}//' -e '/^!/d'; }
fail() { printf 'frame-stats.sh: %s\n' "$1" >&2; exit 2; }

csv="" column="" budget="" skip=0 scale=1
positional=()
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --skip) [ $# -ge 2 ] || fail "--skip needs a number"; skip=$2; shift 2 ;;
    --scale) [ $# -ge 2 ] || fail "--scale needs a number"; scale=$2; shift 2 ;;
    --*) fail "unknown option $1" ;;
    *) positional+=("$1"); shift ;;
  esac
done
[ ${#positional[@]} -ge 2 ] && [ ${#positional[@]} -le 3 ] || { usage >&2; exit 2; }
csv=${positional[0]} column=${positional[1]} budget=${positional[2]:-}

number='^[-+]?([0-9]+[.]?[0-9]*|[.][0-9]+)([eE][-+]?[0-9]+)?$'
[[ $skip =~ ^[0-9]+$ ]] || fail "--skip takes a whole number, not '$skip'"
[[ $scale =~ $number ]] || fail "--scale takes a number, not '$scale'"
if [ -n "$budget" ]; then
  [[ $budget =~ $number ]] || fail "the budget is not a number: '$budget'"
  awk -v b="$budget" 'BEGIN { exit !(b + 0 > 0) }' ||
    fail "the budget must be above 0 ms, not '$budget'"
fi
[ -f "$csv" ] && [ -r "$csv" ] || fail "cannot read $csv"

# Pass 1: pick the column, check every value, print the scaled values.
values=$(awk -v col="$column" -v skip="$skip" -v scale="$scale" -v num="$number" '
  BEGIN { FS = "," }
  { sub(/\r$/, "") }
  NR == 1 {
    for (i = 1; i <= NF; i++) {
      h = $i; gsub(/^[ \t"]+|[ \t"]+$/, "", h)
      if (h == col) idx = i
    }
    if (!idx && col ~ /^[0-9]+$/ && col >= 1 && col <= NF) idx = col + 0
    if (!idx) { print "no column \"" col "\" in the header" > "/dev/stderr"; exit 2 }
    next
  }
  /^[ \t]*$/ { next }
  {
    rows++
    if (rows <= skip) next
    v = $idx; gsub(/^[ \t"]+|[ \t"]+$/, "", v)
    if (v !~ num) { print "line " NR ": not a number: \"" v "\"" > "/dev/stderr"; exit 2 }
    printf "%.17g\n", v * scale
  }' "$csv") || fail "$csv was not read (above)"
[ -n "$values" ] || fail "no data row in $csv after skipping $skip"

# Pass 2: sort ascending and read the ranks.
stats=$(printf '%s\n' "$values" | sort -g | awk -v budget="$budget" '
  { v[++n] = $1 + 0; sum += $1; if (budget != "" && $1 + 0 > budget + 0) over++ }
  function rank(k) { return int((k * n + 99) / 100) }
  END {
    printf "n\t%d\nmethod\tnearest-rank\n", n
    printf "p50\t%.10g\np95\t%.10g\np99\t%.10g\n", v[rank(50)], v[rank(95)], v[rank(99)]
    printf "max\t%.10g\nmean\t%.10g\n", v[n], sum / n
    if (budget != "") printf "budget\t%.10g\nover_budget\t%d\nover_share\t%.2f\n", budget, over, 100 * over / n
  }') || fail "the statistics were not computed"

printf 'file\t%s\ncolumn\t%s\nskipped\t%s\n%s\n' "$csv" "$column" "$skip" "$stats"
