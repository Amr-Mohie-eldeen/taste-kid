#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"

create_response=$(curl -sS -X POST "${BASE_URL}/users" -H "Content-Type: application/json" -d '{}')
user_id=$(echo "${create_response}" | jq -r '.id // empty')
if [[ -z "${user_id}" ]]; then
  echo "Failed to create user." >&2
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
  echo "Failed to resolve one or more movie IDs." >&2
  exit 1
fi

curl -sS -X PUT "${BASE_URL}/users/${user_id}/ratings/${interstellar_id}" \
  -H "Content-Type: application/json" -d '{"rating":5}' >/dev/null
curl -sS -X PUT "${BASE_URL}/users/${user_id}/ratings/${batman_id}" \
  -H "Content-Type: application/json" -d '{"rating":4}' >/dev/null
curl -sS -X PUT "${BASE_URL}/users/${user_id}/ratings/${johnwick_id}" \
  -H "Content-Type: application/json" -d '{"rating":5}' >/dev/null

echo "--- Profile ---"
curl -sS "${BASE_URL}/users/${user_id}/profile" | jq .

echo "--- Profile Norm (before extra rating) ---"
before_norm=$(curl -sS "${BASE_URL}/users/${user_id}/profile" | jq -r '.embedding_norm // empty')
echo "embedding_norm=${before_norm}"

echo "--- Ratings ---"
curl -sS "${BASE_URL}/users/${user_id}/ratings?k=5" | jq .

echo "--- Next Movie ---"
next_movie=$(curl -sS "${BASE_URL}/users/${user_id}/next")
echo "${next_movie}" | jq .
next_id=$(echo "${next_movie}" | jq -r '.id // empty')

if [[ -z "${next_id}" ]]; then
  echo "Failed to fetch next movie." >&2
  exit 1
fi

echo "--- Mark Next as Unwatched ---"
curl -sS -X PUT "${BASE_URL}/users/${user_id}/ratings/${next_id}" \
  -H "Content-Type: application/json" -d '{"status":"unwatched"}' >/dev/null

echo "--- Rate Next Movie (5) ---"
curl -sS -X PUT "${BASE_URL}/users/${user_id}/ratings/${next_id}" \
  -H "Content-Type: application/json" -d '{"rating":5}' >/dev/null

echo "--- Profile Norm (after extra rating) ---"
after_norm=$(curl -sS "${BASE_URL}/users/${user_id}/profile" | jq -r '.embedding_norm // empty')
echo "embedding_norm=${after_norm}"

echo "--- Recommendations ---"
curl -sS "${BASE_URL}/users/${user_id}/recommendations?k=5" | jq .
