#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"

create_response=$(curl -sS -X POST "${BASE_URL}/users" -H "Content-Type: application/json" -d '{}')
user_id=$(echo "${create_response}" | jq -r '.id // empty')
if [[ -z "${user_id}" ]]; then
  echo "Failed to create user."
  exit 1
fi

lookup_id() {
  local title="$1"
  local response
  response=$(curl -sS -G --data-urlencode "title=${title}" "${BASE_URL}/movies/lookup")
  echo "${response}" | jq -r '.id // empty'
}

interstellar_id=$(lookup_id "Interstellar")
batman_id=$(lookup_id "The Batman")
johnwick_id=$(lookup_id "John Wick")

if [[ -z "${interstellar_id}" || -z "${batman_id}" || -z "${johnwick_id}" ]]; then
  echo "Failed to resolve one or more movie IDs."
  exit 1
fi

curl -sS -X PUT "${BASE_URL}/users/${user_id}/ratings/${interstellar_id}" \
  -H "Content-Type: application/json" -d '{"rating":5}' >/dev/null
curl -sS -X PUT "${BASE_URL}/users/${user_id}/ratings/${batman_id}" \
  -H "Content-Type: application/json" -d '{"rating":4}' >/dev/null
curl -sS -X PUT "${BASE_URL}/users/${user_id}/ratings/${johnwick_id}" \
  -H "Content-Type: application/json" -d '{"rating":5}' >/dev/null

echo "User ${user_id} recommendations:"
curl -sS "${BASE_URL}/users/${user_id}/recommendations?k=20" | jq .
