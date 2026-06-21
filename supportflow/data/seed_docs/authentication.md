# Authentication and API Tokens
tags: auth, tokens, 401, developer-api

DevPortal API uses bearer tokens in the `Authorization` header.

Use this format:

```http
Authorization: Bearer <api_token>
```

Common causes of `401 Unauthorized`:

- The token belongs to sandbox but the request uses the production base URL.
- The token has expired or was rotated.
- The `Bearer` prefix is missing.
- The token was copied with extra whitespace.
- The account is disabled or the workspace was archived.

Troubleshooting:

1. Confirm the base URL matches the token environment.
2. Reissue a fresh token from the dashboard.
3. Send a minimal `GET /v1/account` request.
4. Capture the `x-request-id` response header and timestamp.

