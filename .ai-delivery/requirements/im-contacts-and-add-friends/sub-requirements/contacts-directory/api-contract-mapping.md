<!-- ai-delivery-meta: {"version":1,"updated_at":"2026-04-25T00:00:00.000Z","updated_by":"codex"} -->

# API Contract Mapping

## Contract Status

- `status`: `mapped`
- `source`: `contracts/im-contacts.openapi.json`

## Operation Coverage

- `GET /im/contacts`
- `POST /im/friends/invitations`

## Action Side Effects Matrix

| Action | API Operation | Side Effect | Revalidation |
| --- | --- | --- | --- |
| Load contacts directory | `GET /im/contacts` | Reads current contact groups | Revalidate list freshness |
| Send add-friend invite | `POST /im/friends/invitations` | Creates pending invitation | Revalidate contacts and pending invitations |
