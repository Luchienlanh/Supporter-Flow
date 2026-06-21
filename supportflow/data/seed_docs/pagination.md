# Pagination
tags: pagination, cursor, list-api

List endpoints use cursor pagination.

Example:

```http
GET /v1/customers?limit=50
```

The response includes:

```json
{
  "data": [],
  "next_cursor": "eyJpZCI6..."
}
```

To fetch the next page, pass `cursor=<next_cursor>`. Do not parse the cursor. It is opaque and can change format.

Troubleshooting missing records:

1. Check filters and sort order.
2. Follow `next_cursor` until it is null.
3. Confirm the token has access to the workspace that owns the records.

