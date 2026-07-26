#!/usr/bin/env bash
set -euo pipefail

API_BASE_URL="${AIOS_API_BASE_URL:-http://127.0.0.1:8000/api/v1}"
export COMPOSE_PROJECT_NAME="${AIOS_COMPOSE_PROJECT_NAME:-aios_persistence_check_direct_pgdata}"
export AIOS_POSTGRES_VOLUME_DIR="${AIOS_POSTGRES_VOLUME_DIR:-/tmp/${COMPOSE_PROJECT_NAME}-postgres-data}"
MARKER="PERSIST$$_$(date +%s)"
MARKET="CN"

mkdir -p "${AIOS_POSTGRES_VOLUME_DIR}"
docker run --rm -v "${AIOS_POSTGRES_VOLUME_DIR}:/data" busybox \
  sh -c "chown 70:70 /data && chmod 700 /data"

wait_for_api() {
  for _ in $(seq 1 60); do
    if curl -fsS "${API_BASE_URL}/health" >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  echo "AIOS API did not become healthy at ${API_BASE_URL}/health" >&2
  return 1
}

assert_watchlist_present() {
  local response
  response="$(
    curl -fsS \
      "${API_BASE_URL}/research/watchlist?status=active&market=${MARKET}&symbol=${MARKER}"
  )"
  if [[ "${response}" != *"${MARKER}"* ]]; then
    echo "Persisted watchlist marker ${MARKER} was not found" >&2
    echo "${response}" >&2
    return 1
  fi
}

echo "Starting AIOS Compose services..."
docker compose up -d postgres backend
wait_for_api

echo "Creating persistence marker ${MARKER}..."
curl -fsS \
  -X POST \
  -H "Content-Type: application/json" \
  -d "{\"symbol\":\"${MARKER}\",\"market\":\"${MARKET}\",\"note\":\"docker persistence verification\"}" \
  "${API_BASE_URL}/research/watchlist" >/dev/null

assert_watchlist_present

echo "Restarting Postgres and backend containers..."
docker compose restart postgres backend
wait_for_api
assert_watchlist_present

echo "Stopping Compose services without removing volumes..."
docker compose down

echo "Starting AIOS Compose services again..."
docker compose up -d postgres backend
wait_for_api
assert_watchlist_present

echo "Docker persistence verification passed for marker ${MARKER}."
