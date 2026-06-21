# Idempotency Keys
tags: idempotency, retries, post, duplicate

For create and charge-like operations, clients should send an `Idempotency-Key` header.

Rules:

- Use a unique key per logical operation.
- Reuse the same key only when retrying the same request.
- Do not reuse a key with a different payload.
- Store keys for at least 24 hours on the client side.

If a user reports duplicate resources, check whether retries were sent without an idempotency key.

