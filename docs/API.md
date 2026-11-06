# API Overview

Base URL: `/api/`. Interactive docs: `/api/schema/swagger-ui/`.

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/auth/register/` | Register a user |
| POST | `/token/` | Obtain JWT access and refresh tokens |
| POST | `/token/refresh/` | Refresh the access token |
| GET/POST | `/workspaces/` | List or create workspaces (creator becomes OWNER; default statuses are created) |
| POST | `/workspaces/{id}/report/` | Queue a Celery report job (owner or admin) |
| GET/POST | `/projects/` | List or create projects (project key is made unique automatically) |
| GET/POST | `/boards/` | List or create boards |
| GET/POST | `/statuses/` | List or create workflow statuses |
| GET/POST | `/sprints/` | List or create sprints |
| GET/POST/PATCH | `/issues/` | List, create or update issues (including `sprint`) |
| PATCH | `/issues/{id}/move/` | Move an issue to another workflow status |
| GET/POST | `/comments/` | List or create comments |
| GET/POST | `/attachments/` | List or upload attachments (`?issue=<id>` filters by issue) |
| GET | `/audit-events/` | Read audit events |
| POST | `/billing/checkout/` | Create a Stripe subscription Checkout session (owner or admin) |
| POST | `/billing/webhook/` | Receive Stripe events |
| GET | `/health/` | Health check |

## Conventions
- Send `Authorization: Bearer <access_token>` on every request except register, token and webhook.
- Tenant resources are filtered to workspaces where the caller is a member. Pass `?workspace=<id>` to narrow a list.
- For create requests send the selected `workspace` id. Related objects (project, status, sprint, board) must belong to that workspace.

## Error codes
| Code | Meaning |
|---|---|
| 401 | Missing or expired token |
| 402 | FREE plan limit reached (upgrade to PRO) |
| 403 | Not a member of the workspace, role not allowed (for example VIEWER writing), or related object from another workspace |
| 404 | Object does not exist or belongs to a workspace the caller cannot see |