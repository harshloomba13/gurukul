# Gurukul Executor

Shared browser-execution backend with a CrossFit BC/Wodify adapter. `POST /v1/purchases/prepare` collects a live cart total and returns a ten-minute signed quote. Only `POST /v1/purchases/approve`, with `approve: true`, the unchanged token, and an `Idempotency-Key` header, can continue the operation. An idempotency key is bound to its first quote and cannot be reused for a different quote.

Browser state is AES-256-GCM encrypted on disk and security events are appended to a JSONL audit log without tokens or secrets. Real checkout is deliberately disabled in `WodifyAdapter.purchase`; this deployment can prepare quotes but **cannot submit a purchase** until that method and its site selectors receive an explicit, separately reviewed change.

## Configuration

- `EXECUTOR_API_KEY`: bearer credential for both endpoints
- `QUOTE_SIGNING_KEY`: HMAC key for quote tokens
- `SESSION_ENCRYPTION_KEY`: encryption key material for browser state
- `WODIFY_STORE_URL`: approved CrossFit BC Wodify storefront URL
- `SESSION_DIR`, `AUDIT_LOG`: optional persistent-disk paths

Run `npm install && npm test` locally. The root Render Blueprint provisions a persistent disk and prompts for the storefront URL; generated secret values remain server-side.
