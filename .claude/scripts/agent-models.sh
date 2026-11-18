#!/usr/bin/env bash
# agent-models.sh — keep each agent's `model:` and `effort:` equal to
# .claude/agent-models.yaml, the one table that sets them (fix plan AM38).
#
# Claude Code reads a subagent's model and effort only from its frontmatter, so
# the table is copied into every .claude/agents/*.md file. `check` reports where
# a file and the table differ; `sync` writes the table's values.
#
# OBSERVATIONS, NOT A VERDICT (CLAUDE.md, "Helpers in .claude/scripts/"): `check`
# lists differences and grammar errors; which tier a role should have is the
# table's, decided by people.
#
# WRITES only under `sync`, and only the `model:` line of each agent's
# frontmatter and the `effort:` line directly after it. Body lines, other
# frontmatter lines and each file's line endings stay as they are.
#
# Usage: bash .claude/scripts/agent-models.sh check [--root DIR]
#        bash .claude/scripts/agent-models.sh sync [--dry-run] [--root DIR]
#   check       exit 0 when every agent matches the table; exit 1 and print one
#               line per difference or table error
#   sync        write the table's values into the agents; --dry-run prints the
#               agents it would change and writes nothing
#   --root DIR  the project; defaults to the repo this script is in
#   -h, --help  this text
#
# Table grammar (one line-based reader, below; yaml-get.awk reads one scalar
# per call and merges repeated keys, so it cannot report a duplicate):
#   top-level keys `tiers:`, `agents:` and `overrides:` only
#   tiers at two spaces, each with `model:`, `effort:` and optionally
#   `optional: true` at four; the tiers in file order are the escalation ladder
#   and must rise strictly; only the last may be optional
#   agents and overrides as `name: tier` at two spaces; `session` (only under
#   overrides) means `model: inherit` and no `effort:` line
#   a trailing ` # comment` is allowed; tabs, duplicate keys and flow forms
#   ({...} or [...]) are errors
#
# Output of check: `agent<TAB>field<TAB>table<TAB>file` per difference, and
# `table<TAB>error<TAB><message>` per table error.
set -u

usage() { sed -n '2,/^set -u/p' "$0" | sed '$d' | sed 's/^# \{0,1\}//'; }

cmd="${1:-}"
[ $# -gt 0 ] && shift
root=""
dry=0
while [ $# -gt 0 ]; do
  case "$1" in
    --root)
      if [ $# -lt 2 ] || [ -z "$2" ]; then echo "agent-models.sh: --root needs a directory" >&2; exit 2; fi
      root="$2"; shift 2 ;;
    --dry-run) dry=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "agent-models.sh: unknown argument: $1" >&2; exit 2 ;;
  esac
done
case "$cmd" in
  check|sync) ;;
  -h|--help) usage; exit 0 ;;
  *) usage >&2; exit 2 ;;
esac
if [ -z "$root" ]; then
  root="$(cd "$(dirname "$0")/../.." && pwd)"
fi
table="$root/.claude/agent-models.yaml"
agents_dir="$root/.claude/agents"
if [ ! -f "$table" ]; then
  printf 'table\terror\t%s does not exist\n' ".claude/agent-models.yaml"
  exit 1
fi

# The agent files, one name per line.
agent_files="$(for f in "$agents_dir"/*.md; do [ -f "$f" ] && basename "$f" .md; done)"

# Read the table. Prints `E<TAB>message` per error and `X<TAB>agent<TAB>model<TAB>effort`
# per agent (effort `-` for session), after checking the agents against the files.
resolved="$(printf '%s\n' "$agent_files" | AGENT_MODELS_TABLE="$table" awk '
function err(m) { print "E\t" m; bad = 1 }
BEGIN {
  split("haiku sonnet opus fable", m); for (i in m) mrank[m[i]] = i
  split("low medium high xhigh max", e); for (i in e) erank[e[i]] = i
  # The path comes through the environment: `awk -v` would read the
  # backslashes of a Windows path as escapes.
  table = ENVIRON["AGENT_MODELS_TABLE"]
  ntiers = 0; section = ""; current = ""
  while ((rc = (getline line < table)) > 0) {
    n++
    sub(/\r$/, "", line)
    if (line ~ /\t/) { err("line " n ": tab"); continue }
    if (line ~ /^[ ]*$/ || line ~ /^[ ]*#/) continue
    c = index(line, " #"); if (c > 0) line = substr(line, 1, c - 1)
    sub(/[ ]+$/, "", line)
    if (line ~ /^[^ ]/) {
      if (line !~ /^[a-z_]+:$/) { err("line " n ": top-level key with a value or flow form"); continue }
      key = substr(line, 1, length(line) - 1)
      if (key != "tiers" && key != "agents" && key != "overrides") err("line " n ": unknown top-level key " key)
      if (key in seentop) err("line " n ": duplicate key " key)
      seentop[key] = 1; section = key; current = ""; continue
    }
    if (line ~ /^  [a-z0-9][a-z0-9-]*:$/ && section == "tiers") {
      current = substr(line, 3, length(line) - 3)
      if (current in tiermodel || current in seentier) err("line " n ": duplicate key " current)
      seentier[current] = 1; order[++ntiers] = current; continue
    }
    if (line ~ /^  [a-z0-9][a-z0-9-]*: [^ ]+$/ && (section == "agents" || section == "overrides")) {
      split(substr(line, 3), kv, ": ")
      if (kv[2] ~ /^[{[]/) err("line " n ": flow form")
      if (section == "agents") {
        if (kv[1] in agent) err("line " n ": duplicate key " kv[1])
        agent[kv[1]] = kv[2]
      } else {
        if (kv[1] in override) err("line " n ": duplicate key " kv[1])
        override[kv[1]] = kv[2]
      }
      continue
    }
    if (line ~ /^    [a-z]+: [^ ]+$/ && section == "tiers" && current != "") {
      split(substr(line, 5), kv, ": ")
      f = kv[1]; v = kv[2]
      if (f != "model" && f != "effort" && f != "optional") err("line " n ": unknown tier field " f)
      if ((current SUBSEP f) in field) err("line " n ": duplicate key " f)
      if (v ~ /^[{[]/) err("line " n ": flow form")
      field[current SUBSEP f] = v; continue
    }
    t = line; sub(/^[ ]+/, "", t)
    err("line " n ": not in the grammar: " t)
  }
  if (rc < 0) err("cannot read " table)
  close(table)
  prevm = 0; preve = 0
  for (i = 1; i <= ntiers; i++) {
    t = order[i]; mo = field[t SUBSEP "model"]; ef = field[t SUBSEP "effort"]
    op = ((t SUBSEP "optional") in field) ? field[t SUBSEP "optional"] : "false"
    if (!(mo in mrank)) err("tier " t ": unknown model " mo)
    if (!(ef in erank)) err("tier " t ": unknown effort " ef)
    if (op != "true" && op != "false") err("tier " t ": optional must be true or false")
    if (op == "true" && i != ntiers) err("tier " t ": only the last tier may be optional")
    if ((mo in mrank) && (ef in erank)) {
      if (i > 1 && (mrank[mo] < prevm || (mrank[mo] == prevm && erank[ef] <= preve)))
        err("tier " t ": not above the tier before it")
      prevm = mrank[mo]; preve = erank[ef]
    }
    tiermodel[t] = mo; tiereffort[t] = ef
  }
  for (a in agent) {
    if (agent[a] == "session") err("agent " a ": session is allowed only under overrides")
    else if (!(agent[a] in tiermodel)) err("agent " a ": unknown tier " agent[a])
  }
  for (a in override) {
    if (override[a] != "session" && !(override[a] in tiermodel)) err("override " a ": unknown tier " override[a])
    if (!(a in agent)) err("override " a ": no such agent in agents")
  }
}
NF { file[$0] = 1; if (!($0 in agent)) err("agent " $0 ": file has no entry in the table") }
END {
  for (a in agent) if (!(a in file)) err("agent " a ": entry has no file under .claude/agents/")
  if (bad) exit 0
  for (a in agent) {
    t = (a in override) ? override[a] : agent[a]
    if (t == "session") print "X\t" a "\tinherit\t-"
    else print "X\t" a "\t" tiermodel[t] "\t" tiereffort[t]
  }
}')"

errors="$(printf '%s\n' "$resolved" | awk -F'\t' '$1 == "E" { print "table\terror\t" $2 }')"
if [ -n "$errors" ]; then
  printf '%s\n' "$errors" | sort
  exit 1
fi

# The model and effort a frontmatter carries: `model<TAB>effort` (`-` when absent).
read_front() {
  awk '
    { sub(/\r$/, "") }
    /^---[ ]*$/ { dashes++; if (dashes == 2) exit; next }
    dashes == 1 && /^model:/ && model == "" { v = $0; sub(/^model:[ ]*/, "", v); gsub(/["'\'']/, "", v); model = v }
    dashes == 1 && /^effort:/ && effort == "" { v = $0; sub(/^effort:[ ]*/, "", v); gsub(/["'\'']/, "", v); effort = v }
    END { print (model == "" ? "-" : model) "\t" (effort == "" ? "-" : effort) }
  ' "$1"
}

# Rewrite one file's frontmatter: the model line, then the effort line or none.
write_front() {
  local file="$1" model="$2" effort="$3" tmp
  tmp="$(mktemp)"
  # BINMODE=3: gawk on Windows (Git Bash) otherwise drops each CR it reads and
  # writes, turning a CRLF file into LF; elsewhere the variable has no effect.
  awk -v model="$model" -v effort="$effort" '
    BEGIN { BINMODE = 3 }
    {
      line = $0; cr = ""
      if (line ~ /\r$/) { cr = "\r"; sub(/\r$/, "", line) }
      if (line ~ /^---[ ]*$/) { dashes++; print $0; next }
      if (dashes == 1 && line ~ /^effort:/) next
      if (dashes == 1 && line ~ /^model:/ && !done) {
        print "model: " model cr
        if (effort != "-") print "effort: " effort cr
        done = 1; next
      }
      print $0
    }
  ' "$file" > "$tmp"
  if cmp -s "$tmp" "$file"; then rm -f "$tmp"; return 1; fi
  cat "$tmp" > "$file"; rm -f "$tmp"; return 0
}

status=0
while IFS="$(printf '\t')" read -r kind agent model effort; do
  [ "$kind" = "X" ] || continue
  file="$agents_dir/$agent.md"
  have="$(read_front "$file")"
  have_model="${have%%$'\t'*}"
  have_effort="${have#*$'\t'}"
  if [ "$cmd" = "check" ]; then
    if [ "$have_model" != "$model" ]; then
      printf '%s\tmodel\t%s\t%s\n' "$agent" "$model" "$have_model"; status=1
    fi
    if [ "$have_effort" != "$effort" ]; then
      printf '%s\teffort\t%s\t%s\n' "$agent" "$effort" "$have_effort"; status=1
    fi
  elif [ "$have_model" != "$model" ] || [ "$have_effort" != "$effort" ]; then
    if [ "$have_model" = "-" ]; then
      printf '%s\terror\tno model: line in the frontmatter; add one, then run sync\n' "$agent"
      status=1
    elif [ "$dry" = 1 ]; then
      printf '%s\twould change\t%s %s\t%s %s\n' "$agent" "$model" "$effort" "$have_model" "$have_effort"
    else
      write_front "$file" "$model" "$effort" && printf '%s\tchanged\t%s %s\n' "$agent" "$model" "$effort"
    fi
  fi
done <<EOF
$(printf '%s\n' "$resolved" | sort)
EOF
exit "$status"
