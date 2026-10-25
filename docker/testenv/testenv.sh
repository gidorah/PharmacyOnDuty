#!/usr/bin/env bash
# Full dev stack (django, worker, beat, flower, db, redis) for one run, one
# Compose project per worktree. Run from inside the worktree.
#
#   testenv.sh prepare <run-name>   copy .env in, build images
#   testenv.sh start                bring the stack up and wait for validate
#   testenv.sh validate             check the stack itself; must pass first
#   testenv.sh check                validate, then ruff, format, mypy, pytest
#   testenv.sh reset [name|--all]   save logs, down -v, remove leftovers
#
# Also: exec <service> <cmd...>, logs, ps, stats, measure.
set -euo pipefail

PREFIX=pod-
SERVICES=(django worker beat flower db redis)
UV_CACHE_VOLUME=pod-testenv-uv-cache
START_TIMEOUT=${TESTENV_START_TIMEOUT:-600}

ROOT=$(git rev-parse --show-toplevel)
STATE_HOME=${TESTENV_STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/pod-testenv}
NAME_FILE="$ROOT/.testenv"

die() { echo "testenv: $*" >&2; exit 1; }
log() { echo "testenv: $*" >&2; }
stamp() { date -u +%Y%m%dT%H%M%SZ; }

if docker compose version >/dev/null 2>&1; then
  COMPOSE_BIN=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_BIN=(docker-compose)
else
  die "neither 'docker compose' nor 'docker-compose' found"
fi

run_name() {
  [[ -f "$NAME_FILE" ]] || die "no run in $ROOT; run 'prepare <run-name>' first"
  cat "$NAME_FILE"
}

state_dir() { echo "$STATE_HOME/$1"; }

compose_as() {
  local name=$1; shift
  "${COMPOSE_BIN[@]}" -p "$name" --project-directory "$ROOT" \
    --env-file "$ROOT/.env" --env-file "$ROOT/docker/dev/automation.env" \
    -f "$ROOT/docker/dev/docker-compose.yml" -f "$ROOT/docker/testenv/compose.yml" \
    "$@"
}

compose() { compose_as "$(run_name)" "$@"; }

env_value() { grep -E "^$1=" "$ROOT/.env" | tail -n1 | cut -d= -f2- || true; }

set_env() {
  local key=$1 value=$2 file="$ROOT/.env"
  if grep -qE "^$key=" "$file"; then
    KEY="$key" VALUE="$value" python3 - "$file" <<'PY'
import os, sys
path, key, value = sys.argv[1], os.environ["KEY"], os.environ["VALUE"]
lines = open(path).read().splitlines()
out = [f"{key}={value}" if line.startswith(f"{key}=") else line for line in lines]
open(path, "w").write("\n".join(out) + "\n")
PY
  else
    printf '%s=%s\n' "$key" "$value" >>"$file"
  fi
}

unset_env() { sed -i "/^$1=/d" "$ROOT/.env"; }

main_checkout() { git worktree list --porcelain | awk 'NR==1 {print $2}'; }

# The worktree gets its own .env. Source: $TESTENV_ENV_FILE, else the main
# checkout's .env, else .env.example. Then force the values a test stack needs.
write_env() {
  local src=${TESTENV_ENV_FILE:-}
  if [[ -z "$src" ]]; then
    src="$(main_checkout)/.env"
    [[ -f "$src" ]] || src="$ROOT/.env.example"
  fi
  [[ -f "$src" ]] || die "env source $src not found"
  if [[ "$(realpath "$src")" != "$(realpath -m "$ROOT/.env")" ]]; then
    cp "$src" "$ROOT/.env"
  fi
  log "env copied from $src"

  local redis_password secret_key
  redis_password=$(env_value REDIS_PASSWORD)
  [[ -n "$redis_password" ]] || redis_password=testenv-$(openssl rand -hex 8)
  secret_key=$(env_value DJANGO_SECRET_KEY)
  [[ -n "$secret_key" && "$secret_key" != change-me* ]] || secret_key=$(openssl rand -hex 32)

  set_env SENTRY_DSN ""
  # Tests reload settings with this unset; a value in .env would come back.
  unset_env DJANGO_ENABLE_SECURE_PROXY_SSL_HEADER
  [[ -n "$(env_value GOOGLE_MAPS_API_KEY)" ]] || set_env GOOGLE_MAPS_API_KEY testenv-dummy-key
  set_env DJANGO_SECRET_KEY "$secret_key"
  set_env DJANGO_ALLOWED_HOSTS "localhost 127.0.0.1 django"
  set_env DJANGO_SECURE_SSL_REDIRECT False
  set_env DJANGO_SESSION_COOKIE_SECURE False
  set_env DJANGO_CSRF_COOKIE_SECURE False
  set_env DB_HOST db
  set_env DB_PORT 5432
  set_env DB_USER postgres
  set_env DB_PASSWORD password
  set_env REDIS_PASSWORD "$redis_password"
  set_env CELERY_BROKER_URL "redis://:$redis_password@redis:6379/0"
}

cmd_prepare() {
  local name=${1:-}
  [[ -n "$name" ]] || die "usage: prepare <run-name>"
  [[ "$name" == "$PREFIX"* ]] || name="$PREFIX$name"
  name=$(echo "$name" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9_\n-' '-')

  if [[ -f "$NAME_FILE" && "$(cat "$NAME_FILE")" != "$name" ]]; then
    log "worktree had run $(cat "$NAME_FILE"); resetting it"
    cmd_reset "$(cat "$NAME_FILE")"
  fi
  if project_exists "$name"; then
    log "a stack named $name already exists; resetting it"
    cmd_reset "$name"
  fi

  echo "$name" >"$NAME_FILE"
  mkdir -p "$(state_dir "$name")/logs"
  write_env

  docker volume inspect "$UV_CACHE_VOLUME" >/dev/null 2>&1 || docker volume create "$UV_CACHE_VOLUME" >/dev/null
  compose build ${TESTENV_NO_CACHE:+--no-cache} 2>&1 | tee "$(state_dir "$name")/logs/build.log" >&2
  compose run --rm --no-deps --user root --entrypoint chown django \
    1000:1000 /home/python/.cache/uv >/dev/null
  log "prepared $name (state in $(state_dir "$name"))"
}

cmd_start() {
  local name t0
  name=$(run_name)
  t0=$(date +%s)
  compose up -d "${SERVICES[@]}" >&2
  log "waiting for validate (up to ${START_TIMEOUT}s)"
  until cmd_validate >/dev/null 2>&1; do
    if [[ -n "$(compose ps -a --status exited --services django worker flower 2>/dev/null)" ]]; then
      cmd_validate || true
      die "an app container exited; logs: testenv.sh logs"
    fi
    if (( $(date +%s) - t0 > START_TIMEOUT )); then
      cmd_validate || true
      die "stack did not validate within ${START_TIMEOUT}s; logs: testenv.sh logs"
    fi
    sleep 5
  done
  # Tests render templates with the manifest storage, so static must be collected.
  compose exec -T django uv run python manage.py collectstatic --noinput >/dev/null
  log "started $name in $(( $(date +%s) - t0 ))s"
  echo "django http://$(compose port django 8000)"
  echo "flower http://$(compose port flower 5555)"
}

# grep without -q: with pipefail, an early exit would fail the pipe on SIGPIPE.
redis_ping() { compose exec -T redis redis-cli --no-auth-warning -a "$1" ping | grep PONG >/dev/null; }
beat_started() { compose logs beat | grep 'beat: Starting' >/dev/null; }

# One line per check; exits non-zero if any check fails.
cmd_validate() {
  local failed=0 running redis_password
  redis_password=$(env_value REDIS_PASSWORD)
  check() {
    local label=$1; shift
    if "$@" >/dev/null 2>&1; then echo "PASS $label"; else echo "FAIL $label"; failed=1; fi
  }
  running=$(compose ps --status running --services 2>/dev/null || true)
  for s in "${SERVICES[@]}"; do
    check "$s running" grep -qx "$s" <<<"$running"
  done
  check "db accepts connections" compose exec -T db pg_isready -U postgres
  check "redis answers ping" redis_ping "$redis_password"
  check "django system check" compose exec -T django uv run python manage.py check
  check "migrations applied" compose exec -T django uv run python manage.py migrate --check
  check "django serves /robots.txt" compose exec -T django curl -fsS http://localhost:8000/robots.txt
  check "worker answers celery ping" compose exec -T worker uv run celery -A PharmacyOnDuty inspect ping -t 10
  check "beat started" beat_started
  check "flower healthcheck" compose exec -T flower curl -fsS http://localhost:5555/healthcheck
  return $failed
}

# Runs every step to the end; output goes to the run's log folder.
cmd_check() {
  local name dir failed=0 t0
  name=$(run_name)
  dir="$(state_dir "$name")/logs/check-$(stamp)"
  mkdir -p "$dir"
  cmd_validate | tee "$dir/validate.log" || die "validate failed; no test result counts"
  step() {
    local label=$1; shift
    t0=$(date +%s)
    if compose exec -T django "$@" >"$dir/$label.log" 2>&1; then
      echo "PASS $label ($(( $(date +%s) - t0 ))s)"
    else
      echo "FAIL $label ($(( $(date +%s) - t0 ))s) see $dir/$label.log"
      failed=1
    fi
  }
  step ruff uv run ruff check .
  step format uv run ruff format --check .
  step mypy uv run mypy .
  step pytest uv run pytest -p no:cacheprovider
  tail -n 3 "$dir/pytest.log"
  echo "logs: $dir"
  return $failed
}

cmd_exec() { compose exec -T "$@"; }

cmd_logs() {
  local name dir
  name=${1:-$(run_name)}
  dir="$(state_dir "$name")/logs"
  mkdir -p "$dir"
  for s in "${SERVICES[@]}"; do
    compose_as "$name" logs --no-color "$s" >"$dir/$s.log" 2>&1 || true
  done
  echo "$dir"
}

project_exists() {
  [[ -n "$(docker ps -aq --filter "label=com.docker.compose.project=$1")$(docker volume ls -q --filter "label=com.docker.compose.project=$1")" ]]
}

list_runs() {
  { docker ps -a --format '{{.Label "com.docker.compose.project"}}'
    docker volume ls --format '{{.Label "com.docker.compose.project"}}'
    docker network ls --format '{{.Label "com.docker.compose.project"}}'
  } | grep "^$PREFIX" | sort -u || true
}

# No refusal: whatever carries the run's Compose label is removed.
reset_one() {
  local name=$1
  [[ "$name" == "$PREFIX"* ]] || die "refusing names outside $PREFIX*: $name"
  if project_exists "$name"; then
    cmd_logs "$name" >/dev/null
    compose_as "$name" down -v --remove-orphans --rmi local >/dev/null 2>&1 || true
  fi
  docker ps -aq --filter "label=com.docker.compose.project=$name" | xargs -r docker rm -f >/dev/null
  docker volume ls -q --filter "label=com.docker.compose.project=$name" | xargs -r docker volume rm -f >/dev/null
  docker network ls -q --filter "label=com.docker.compose.project=$name" | xargs -r docker network rm >/dev/null
  docker images -q --filter "label=com.docker.compose.project=$name" | xargs -r docker rmi -f >/dev/null 2>&1 || true
  log "reset $name (logs kept in $(state_dir "$name")/logs)"
}

cmd_reset() {
  local target=${1:-}
  if [[ "$target" == --all ]]; then
    for n in $(list_runs); do reset_one "$n"; done
    return
  fi
  [[ -n "$target" ]] || target=$(run_name)
  [[ "$target" == "$PREFIX"* ]] || target="$PREFIX$target"
  reset_one "$target"
  if [[ -f "$NAME_FILE" && "$(cat "$NAME_FILE")" == "$target" ]]; then rm -f "$NAME_FILE"; fi
}

cmd_ps() { compose ps; }

# Memory per container right now, and the total in MiB.
cmd_stats() {
  local ids
  ids=$(compose ps -q)
  [[ -n "$ids" ]] || die "no containers running"
  # shellcheck disable=SC2086
  docker stats --no-stream --format '{{.Name}} {{.MemUsage}}' $ids |
    awk '{ v=$2; u=v; gsub(/[0-9.]/,"",u); gsub(/[^0-9.]/,"",v);
           m = (u=="GiB") ? v*1024 : (u=="KiB") ? v/1024 : (u=="B") ? v/1048576 : v;
           printf "%s %.0f MiB\n", $1, m; t+=m } END { printf "total %.0f MiB\n", t }'
}

# Phase 0 measurement: cold and warm start, peak memory, disk, check time.
# Cold means a no-cache build and an empty uv cache; pulled base images stay.
cmd_measure() {
  local name=${1:-measure} out t0 peak=0 sampler check_rc
  [[ "$name" == "$PREFIX"* ]] || name="$PREFIX$name"
  out="$(state_dir "$name")/measure-$(stamp).md"
  mkdir -p "$(dirname "$out")"
  {
    echo "# testenv measure $(stamp)"
    echo "commit $(git -C "$ROOT" rev-parse --short HEAD), host $(hostname)"
    echo
  } >"$out"

  cmd_reset "$name" >/dev/null 2>&1 || true
  docker volume rm -f "$UV_CACHE_VOLUME" >/dev/null 2>&1 || true

  t0=$(date +%s); TESTENV_NO_CACHE=1 cmd_prepare "$name" >/dev/null
  echo "- cold prepare (build): $(( $(date +%s) - t0 ))s" >>"$out"
  t0=$(date +%s); cmd_start >/dev/null
  echo "- cold start to validate: $(( $(date +%s) - t0 ))s" >>"$out"

  ( while :; do cmd_stats 2>/dev/null | awk '/^total/ {print $2}'; sleep 2; done ) \
    >"$(state_dir "$name")/mem-samples.txt" &
  sampler=$!
  t0=$(date +%s)
  cmd_check >"$(state_dir "$name")/measure-check.txt" 2>&1 && check_rc=0 || check_rc=$?
  echo "- check (ruff, format, mypy, full pytest): $(( $(date +%s) - t0 ))s, exit $check_rc" >>"$out"
  kill "$sampler" 2>/dev/null || true
  peak=$(sort -n "$(state_dir "$name")/mem-samples.txt" | tail -n1)
  echo "- peak memory during check: ${peak:-?} MiB" >>"$out"
  { echo; echo '```'; cmd_stats; echo '```'; } >>"$out"
  grep -E '^(PASS|FAIL)' "$(state_dir "$name")/measure-check.txt" | sed 's/^/    /' >>"$out" || true
  local pytest_log
  pytest_log="$(sed -n 's/^logs: //p' "$(state_dir "$name")/measure-check.txt")/pytest.log"
  grep -E '^FAILED|^ERROR' "$pytest_log" | sed 's/^/    /' >>"$out" || true
  tail -n1 "$pytest_log" | sed 's/^/- pytest: /' >>"$out" || true
  { echo; echo "Disk:"; echo '```'
    docker images --filter "label=com.docker.compose.project=$name" --format '{{.Repository}} {{.Size}}'
    docker system df -v --format '{{range .Volumes}}{{.Name}} {{.Size}}{{"\n"}}{{end}}' 2>/dev/null |
      grep -E "^($name|$UV_CACHE_VOLUME)" || true
    echo '```'; } >>"$out"

  cmd_reset "$name" >/dev/null
  t0=$(date +%s); cmd_prepare "$name" >/dev/null
  echo "- warm prepare: $(( $(date +%s) - t0 ))s" >>"$out"
  t0=$(date +%s); cmd_start >/dev/null
  echo "- warm start to validate: $(( $(date +%s) - t0 ))s" >>"$out"
  cmd_reset "$name" >/dev/null
  cat "$out"
}

verb=${1:-}
[[ -n "$verb" ]] || { sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }
shift
case "$verb" in
  prepare|start|validate|check|exec|logs|reset|ps|stats|measure) "cmd_$verb" "$@" ;;
  *) die "unknown verb $verb" ;;
esac
