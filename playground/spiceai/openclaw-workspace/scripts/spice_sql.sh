#!/usr/bin/env sh
set -eu

base_url="${OPENCLAW_SPICE_HTTP_URL:-${SPICE_HTTP_URL:-http://host.docker.internal:8090}}"
max_time="${SPICE_CURL_MAX_TIME:-60}"

if [ "$#" -gt 0 ]; then
  sql="$1"
else
  sql="$(cat)"
fi

if [ -z "$sql" ]; then
  echo "usage: spice_sql.sh \"SELECT ...\" or pipe SQL on stdin" >&2
  exit 1
fi

curl --fail --silent --show-error \
  --max-time "$max_time" \
  -X POST \
  "$base_url/v1/sql" \
  -H 'Content-Type: text/plain' \
  --data-binary "$sql"
