# NexTask — Multi-Tenant SaaS Project Management Platform

A Jira-like project management application built for the FS-04 internship assignment.

## Stack
- Backend: Python 3.11+, Django 5.2, Django REST Framework, SimpleJWT
- Database: PostgreSQL
- Frontend: React + Vite
- Background jobs: Celery + Redis
- Billing: Stripe Billing (test mode)
- Containers: Docker Compose
- CI: GitHub Actions

## Implemented foundation
- Shared-schema tenant isolation using `workspace_id` foreign keys and workspace membership checks.
- Workspace, membership, project, board, workflow status, issue, sprint, comment, attachment and audit event models.
- JWT authentication and role-based workspace permissions.
- REST endpoints for core workspace/project/board/issue/sprint/comment operations.
- Issue status updates for Kanban workflow; React Kanban board with drag-and-drop.
- Celery task example for notifications/report jobs.
- Stripe Checkout session creation and webhook endpoint (test mode).
- Docker Compose for PostgreSQL, Redis, backend and frontend.
- GitHub Actions backend checks.

> This is a runnable starter implementation, not a claim of production certification. Configure secrets, run tests, verify Stripe webhooks, and complete a deployment rehearsal before submission.

## Quick start (Docker)
1. Copy `.env.example` to `.env` and set `DJANGO_SECRET_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` as appropriate.
2. Run: `docker compose up --build`
3. Backend: http://localhost:8000
4. API schema: http://localhost:8000/api/schema/swagger-ui/
5. Frontend: http://localhost:5173

On first start, run migrations:
```bash
docker compose exec backend python manage.py migrate
```
Create an admin:
```bash
docker compose exec backend python manage.py createsuperuser
```

## Local development
Backend:
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py runserver
```
Frontend (new terminal):
```bash
cd frontend
npm install
npm run dev
```

## Tenant isolation
Every tenant-owned record is linked to a workspace. API querysets are filtered through the authenticated user's workspace memberships. Never trust a client-supplied workspace ID without checking membership. Roles: `OWNER`, `ADMIN`, `MEMBER`, `VIEWER`.

## Stripe
Set `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET`. Create a Stripe test product/price and set `STRIPE_PRICE_ID`. Checkout uses Stripe test mode. Configure a webhook endpoint at `/api/billing/webhook/` for `checkout.session.completed` and `customer.subscription.*` events. Do not use live keys for development.

## Important next actions
- Add your team/intern details to the reflection and presentation.
- Add screenshots from your own successful local/deployed run.
- Run and record the test suite; do not invent performance numbers.
- Configure a public deployment only after local verification.
