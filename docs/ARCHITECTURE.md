# NexTask Architecture

## Tenant strategy
Shared PostgreSQL schema. Every tenant-owned record has a `workspace` foreign key. A user can reach a record only through a `Membership` in that workspace, so querysets are always filtered by the caller's memberships. When a request names related objects (project, status, sprint, board), the API checks that they belong to the same workspace as the issue.

Roles: `OWNER`, `ADMIN`, `MEMBER` (can write), `VIEWER` (read-only).

## System overview
```mermaid
flowchart LR
    Browser["Browser<br/>React + Vite :5173"] -->|"REST + JWT"| API["Django REST Framework :8000"]
    API -->|"tenant-filtered queries"| DB[("PostgreSQL")]
    API -->|"enqueue task"| Redis[("Redis")]
    Redis --> Worker["Celery worker"]
    Worker --> DB
    API -->|"create Checkout session"| Stripe["Stripe (test mode)"]
    Browser -->|"redirect to pay"| Stripe
    Stripe -->|"webhook events"| API
    API -->|"uploaded files"| Media[("media volume")]
```

## Data model
```mermaid
erDiagram
    WORKSPACE ||--o{ MEMBERSHIP : has
    USER ||--o{ MEMBERSHIP : joins
    WORKSPACE ||--o{ PROJECT : owns
    WORKSPACE ||--o{ WORKFLOW_STATUS : defines
    PROJECT ||--o{ BOARD : has
    PROJECT ||--o{ SPRINT : plans
    PROJECT ||--o{ ISSUE : contains
    WORKFLOW_STATUS ||--o{ ISSUE : "current status"
    SPRINT ||--o{ ISSUE : groups
    ISSUE ||--o{ COMMENT : has
    ISSUE ||--o{ ATTACHMENT : has
    WORKSPACE ||--o{ AUDIT_EVENT : records
```
Every box except `USER` also carries a `workspace_id`.

## Components
| Component | Responsibility |
|---|---|
| React + Vite | Workspace switcher, Kanban board (drag-and-drop), sprints, activity log, issue panel with comments and attachments |
| Django REST Framework | JWT authentication, role checks, workspace-scoped CRUD, plan limits, Stripe endpoints |
| PostgreSQL | All application data |
| Redis + Celery | Background jobs (workspace report, notification task) |
| Stripe Billing | Subscription Checkout and webhook that upgrades a workspace to PRO |
| Docker Compose | Runs db, redis, backend, celery and frontend together |
| GitHub Actions | Runs `manage.py check` and the test suite on every push |

## Main flows
**Moving an issue:** the board sends `PATCH /api/issues/{id}/move/`. The API checks membership and write role, validates the target status belongs to the workspace, saves it, and writes an audit event.

**Generating a report:** `POST /api/workspaces/{id}/report/` (owner or admin) queues `build_workspace_report` in Redis. The Celery worker runs it and logs the result.

**Upgrading a plan:** the app calls `POST /api/billing/checkout/`, the user pays on Stripe, Stripe calls `POST /api/billing/webhook/`, and the backend sets `plan=PRO` and `subscription_status=active` and stores the Stripe customer and subscription ids.

**Plan limits:** on create, FREE workspaces are limited to 3 projects and 10 issues (HTTP 402). PRO is unlimited.