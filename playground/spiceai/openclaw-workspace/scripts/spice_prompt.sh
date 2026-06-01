#!/usr/bin/env sh
set -eu

base_url="${OPENCLAW_SPICE_HTTP_URL:-${SPICE_HTTP_URL:-http://host.docker.internal:8090}}"
model="${SPICE_MODEL:-spice_assistant}"
max_completion_tokens="${SPICE_MAX_COMPLETION_TOKENS:-64}"
temperature="${SPICE_TEMPERATURE:-0}"
max_time="${SPICE_CURL_MAX_TIME:-60}"

if [ "$#" -gt 0 ]; then
  prompt="$*"
else
  prompt="$(cat)"
fi

if [ -z "$prompt" ]; then
  echo "usage: spice_prompt.sh \"your prompt\" or pipe a prompt on stdin" >&2
  exit 1
fi

tmp_json="$(mktemp)"
trap 'rm -f "$tmp_json"' EXIT

python3 - "$prompt" "$model" "$max_completion_tokens" "$temperature" > "$tmp_json" <<'PY'
import json
import sys

prompt, model, max_tokens, temperature = sys.argv[1:5]

payload = {
    "model": model,
    "messages": [
        {
            "role": "user",
            "content": prompt,
        }
    ],
    "max_completion_tokens": int(max_tokens),
    "temperature": float(temperature),
}

json.dump(payload, sys.stdout)
PY

curl --fail --silent --show-error \
  --max-time "$max_time" \
  -X POST \
  "$base_url/v1/chat/completions" \
  -H 'Content-Type: application/json' \
  --data-binary @"$tmp_json"
