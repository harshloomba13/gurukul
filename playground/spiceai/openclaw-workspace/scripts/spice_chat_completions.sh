#!/usr/bin/env sh
set -eu

base_url="${OPENCLAW_SPICE_HTTP_URL:-${SPICE_HTTP_URL:-http://host.docker.internal:8090}}"
max_time="${SPICE_CURL_MAX_TIME:-60}"

curl --fail --silent --show-error \
  --max-time "$max_time" \
  -X POST \
  "$base_url/v1/chat/completions" \
  -H 'Content-Type: application/json' \
  --data-binary @-
