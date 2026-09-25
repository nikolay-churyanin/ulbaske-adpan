#!/bin/bash
DIR="$HOME/projects/ulbaske-adpan"
cd "$DIR" || exit 1
export MPLBACKEND=Agg
export GIT_TERMINAL_PROMPT=0

PYTHON="$DIR/.venv/bin/python"
PIP="$DIR/.venv/bin/pip"
PATTERN="$DIR/.venv/bin/python main.py"
BRANCH="$(git rev-parse --abbrev-ref HEAD)"

is_running() {
  pgrep -f "$PATTERN" >/dev/null
}

stop_bot() {
  if ! is_running; then
    return 0
  fi
  pkill -f "$PATTERN" || true
  for _ in 1 2 3 4 5; do
    is_running || return 0
    sleep 1
  done
  pkill -9 -f "$PATTERN" || true
}

updated=0
if git fetch --quiet origin "$BRANCH"; then
  local_rev="$(git rev-parse HEAD)"
  remote_rev="$(git rev-parse "origin/$BRANCH")"
  if [ "$local_rev" != "$remote_rev" ]; then
    old_req="$(git rev-parse HEAD:requirements.txt 2>/dev/null || true)"
    if git pull --ff-only --quiet origin "$BRANCH"; then
      updated=1
      new_req="$(git rev-parse HEAD:requirements.txt 2>/dev/null || true)"
      if [ -n "$old_req" ] && [ "$old_req" != "$new_req" ]; then
        "$PIP" install -r requirements.txt
      fi
    fi
  fi
fi

if [ "$updated" -eq 1 ]; then
  stop_bot
fi

if is_running; then
  exit 0
fi

exec "$PYTHON" main.py
