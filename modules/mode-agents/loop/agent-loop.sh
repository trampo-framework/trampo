#!/bin/sh
# One tick for an OS timer: agent-loop.sh <workspace> <verb> <agent>. Verb is tick, monitor or release.
# Ticks that find nothing to do print one word; a lock stops a slow tick from overlapping the next.
set -u
ws=${1:?workspace}; verb=${2:?verb}; name=${3:?agent}
lock="$ws/.trampo/state/agent-$name.lock"
mkdir -p "$ws/.trampo/state"
mkdir "$lock" 2>/dev/null || exit 0
# no exec below: the shell must outlive the tick for this to run
trap 'rmdir "$lock" 2>/dev/null' EXIT
trap 'exit 129' HUP INT TERM
here=$(cd "$(dirname "$0")" && pwd)
python3 -B "$here/../../../core/scripts/agent.py" --ws "$ws" "$verb" "$name"
