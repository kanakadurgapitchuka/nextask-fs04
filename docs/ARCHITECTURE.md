# NexTask Architecture

## Tenant strategy
Shared PostgreSQL schema with `workspace_id` on tenant-owned records. A user can access records only through a `Membership` in that workspace. Roles: OWNER, ADMIN, MEMBER, VIEWER.

## Components
- React/Vite: workspace UI and Kanban board.
- Django REST Framework: JWT authentication, workspace-aware API.
- PostgreSQL: users, workspaces, projects, boards, statuses, issues, sprints, comments, attachments and audit events.
- Redis + Celery: asynchronous notification and report tasks.
- Stripe Billing: test-mode subscription checkout and webhook receiver.
- Docker Compose: local multi-service environment.
- GitHub Actions: backend checks and tests.

## Main flow
Browser -> React -> DRF/JWT -> tenant-filtered querysets -> PostgreSQL.
Celery worker consumes tasks from Redis.
Stripe Checkout redirects to Stripe; webhook updates workspace subscription state.
