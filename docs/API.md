# API Overview

Base URL: `/api/`

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/auth/register/` | Register user |
| POST | `/token/` | Obtain JWT |
| POST | `/token/refresh/` | Refresh JWT |
| GET/POST | `/workspaces/` | List/create workspaces |
| GET/POST | `/projects/` | List/create projects |
| GET/POST | `/boards/` | List/create boards |
| GET/POST | `/statuses/` | List/create workflow statuses |
| GET/POST | `/sprints/` | List/create sprints |
| GET/POST | `/issues/` | List/create issues |
| PATCH | `/issues/{id}/move/` | Move issue to a workspace status |
| GET/POST | `/comments/` | List/create comments |
| GET/POST | `/attachments/` | List/upload attachments |
| GET | `/audit-events/` | Read audit events |
| POST | `/billing/checkout/` | Create Stripe subscription Checkout session |
| POST | `/billing/webhook/` | Receive Stripe events |
| GET | `/health/` | Health check |

Authenticated requests use `Authorization: Bearer <access_token>`. Tenant resources are filtered to workspaces where the caller is a member. For create operations, send the selected `workspace` ID and related objects must belong to that workspace.
