# Test Plan

## Automated tests included
- A user sees only workspaces where they have membership.
- Creating a workspace creates the owner membership and default workflow statuses.

Run:
```bash
cd backend
python manage.py test
python manage.py check
```

## Manual end-to-end checklist
- [ ] Register two users and create separate workspaces.
- [ ] Confirm User A cannot list or retrieve User B's tenant data.
- [ ] Create project, board, sprint and issues.
- [ ] Move issue across Kanban statuses.
- [ ] Add comments and upload an attachment.
- [ ] Confirm audit events are recorded.
- [ ] Run Celery worker and execute a report task.
- [ ] Configure Stripe test price and webhook; complete a test checkout.
- [ ] Run Docker Compose from a clean environment.
- [ ] Confirm GitHub Actions succeeds.

Record actual results, environment, date and screenshots after running. Do not report tests as passed until executed.
