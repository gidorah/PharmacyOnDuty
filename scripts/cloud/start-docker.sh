#!/usr/bin/env bash
# SessionStart hook. Cloud sessions (claude.ai/code) ship dockerd but do not
# run it, and the environment snapshot keeps no processes, so every session
# starts it here. testenv.sh needs it. Local sessions exit at once.
# The container can restart while the session is idle, which stops dockerd;
# rerun this script by hand when docker commands fail.
set -euo pipefail

[[ "${CLAUDE_CODE_REMOTE:-}" == "true" ]] || exit 0
docker info >/dev/null 2>&1 && exit 0

sudo=()
[[ $EUID -eq 0 ]] || sudo=(sudo -n)
# setsid: dockerd must outlive the hook's process group.
setsid "${sudo[@]}" dockerd >/tmp/dockerd.log 2>&1 </dev/null &

for _ in $(seq 30); do
  docker info >/dev/null 2>&1 && exit 0
  sleep 1
done
echo "dockerd did not start; see /tmp/dockerd.log" >&2
exit 1
