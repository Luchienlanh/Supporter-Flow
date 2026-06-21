# Rate Limits
tags: rate-limit, 429, retry, headers

The API returns `429 Too Many Requests` when a client exceeds the allowed request rate.

Every rate-limited response includes:

- `x-ratelimit-limit`
- `x-ratelimit-remaining`
- `x-ratelimit-reset`
- `retry-after`

Recommended handling:

1. Respect `retry-after`.
2. Use exponential backoff with jitter.
3. Avoid retrying non-idempotent requests unless the request has an idempotency key.
4. Batch reads when possible.

Escalate to engineering only when rate-limit headers are missing or inconsistent.

