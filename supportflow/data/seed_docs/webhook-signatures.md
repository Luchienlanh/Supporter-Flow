# Webhook Signature Verification
tags: webhooks, signatures, hmac, 400

Webhook events include an `x-devportal-signature` header and `x-devportal-timestamp`.

Verification steps:

1. Build the signed payload as `<timestamp>.<raw_request_body>`.
2. Compute HMAC-SHA256 with the webhook signing secret.
3. Compare using a constant-time comparison.
4. Reject timestamps older than five minutes.

Common causes of signature mismatch:

- The app verifies parsed JSON instead of the raw request body.
- The wrong environment signing secret is used.
- A proxy changes the request body.
- The timestamp is omitted from the signed payload.

