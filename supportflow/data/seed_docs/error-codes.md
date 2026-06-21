# Error Codes
tags: errors, diagnostics, request-id

Every API error response includes:

```json
{
  "error": {
    "code": "invalid_request",
    "message": "Human-readable message",
    "request_id": "req_..."
  }
}
```

Common codes:

- `invalid_request`: required field missing or invalid.
- `unauthorized`: token is missing, expired, or invalid.
- `forbidden`: token is valid but lacks permission.
- `not_found`: resource does not exist in this workspace.
- `rate_limited`: client exceeded request rate.
- `internal_error`: temporary server-side failure.

Support replies should ask for `request_id`, timestamp, endpoint, method, and sanitized request body.

