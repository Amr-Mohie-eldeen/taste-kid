#!/usr/bin/env bash
# Principal AI Engineer Note: Ensure 'jq' is installed (sudo apt install jq)
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"

# 1. Join all arguments into a single string correctly
# Using "$*" within quotes is the standard for multi-word titles
TITLE="${*:-Memento}"

echo "--- Looking up Movie: '$TITLE' ---"

# 2. Use curl --get and --data-urlencode to handle spaces/special chars
# This ensures "Fight Club" becomes "Fight%20Club"
lookup_response=$(curl -sS -G \
  --data-urlencode "title=$TITLE" \
  "$BASE_URL/movies/lookup")

# 3. Use JQ for robust JSON parsing instead of Python
# This handles both a single object or a list of results
movie_id=$(echo "$lookup_response" | jq -r '
  if type == "object" and .id then .id 
  elif .results? and (.results | length > 0) then .results[0].id 
  else empty end
')

if [[ -z "$movie_id" || "$movie_id" == "null" ]]; then
  echo "Error: Movie '$TITLE' not found in database." >&2
  exit 1
fi

echo "--- Found ID: $movie_id. Fetching 20 similar movies... ---"

# 4. Final similarity call
curl -sS "$BASE_URL/movies/$movie_id/similar?k=20" | jq .