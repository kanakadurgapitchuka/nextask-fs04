# Individual Reflection: FS-04 NexTask

**Project:** NexTask, a Multi-Tenant SaaS Project Management Platform
**Repository:** https://github.com/kanakadurgapitchuka/nextask-fs04

## What I Owned

- Set up and ran the full-stack application using Docker Compose: PostgreSQL, Redis, Django REST API, Celery worker, and React (Vite) frontend.
- Configured JWT authentication and tested user registration, login, and workspace data isolation.
- Built and debugged the React Kanban board using `@dnd-kit`, including fixing the issue that prevented cards from moving between all three columns and ensuring status changes persisted after a page refresh.
- Added the Sprints page, issue comments, file attachments, activity (audit) log, and a Settings page for managing workspace members and roles.
- Integrated Stripe Billing in test mode, including Checkout and webhooks to upgrade workspaces to PRO. Implemented FREE plan limits of 3 projects and 10 issues per workspace.
- Triggered a Celery background job for workspace reports through the API and verified its execution in the worker logs.
- Wrote 11 automated tests, configured GitHub Actions for backend tests, frontend builds and Docker image publishing, and prepared the README, architecture documentation and API overview.
- Verified the complete setup from scratch by cloning the repository into a new folder and running `docker compose up --build`.

## How I Worked

I used an AI assistant (Claude) for guidance and code suggestions. I personally ran, tested, and debugged each change. I verified results using automated tests, the browser, the database, and application logs before committing.

## What I Learned

- **Multi-tenancy:** Every tenant-specific record belongs to a workspace, and every query must be filtered by the user's workspace membership. Related objects must be validated too, for example rejecting a sprint from another workspace even when its ID is valid.
- **Role-based access control:** A Viewer must be blocked at the server with a 403 Forbidden response, not just by hiding options in the UI.
- **API design with Django REST Framework:** ViewSets, custom actions, permissions, and HTTP status codes, including 402 for plan limits and 403 for permission restrictions.
- **Frontend state and drag-and-drop:** Drop targets, collision detection, optimistic updates, and reloading data from the server when an API request fails.
- **Background jobs and billing:** How Celery works with Redis, how Stripe Checkout works, and why webhooks are needed. I used the Stripe CLI to forward webhook events to my local backend.
- **Containers and CI:** Docker Compose services, environment variables, keeping secrets out of Git, and running automated tests through GitHub Actions.

## Challenges and Solutions

**1. Drag-and-drop was not working.**
Cards were not moving between columns because the columns were not registered as drop targets, and the collision detection function had a missing import. I made each column a droppable area, excluded the dragged card from target detection, and updated the board immediately while the API request ran.

**2. Stripe webhook on a local machine.**
Stripe could not reach my local backend through localhost. I installed the Stripe CLI, forwarded the three webhook events I needed, stored the signing secret in `.env`, and confirmed a 200 response. I also verified in the database that the workspace plan changed to PRO.

**3. Server error instead of permission error.**
A user without the required access caused a 500 Internal Server Error because the code raised Python's `PermissionError`. I replaced it with Django REST Framework's `PermissionDenied`, which returns a proper 403 Forbidden, and added tests to verify this.

**4. Expired login token.**
The application showed a "token not valid" message after the access token expired. I identified automatic refresh-token handling as a frontend improvement.

**5. Windows and Docker issues.**
I faced issues with folder paths, `.env` changes that required recreating containers, and the Stripe CLI missing from PATH. I solved them step by step by checking application logs and file contents.

## What I Would Improve

- Add email invitations for members who do not have an account yet.
- Add a project picker when creating sprints and support custom workflow columns in the UI.
- Implement Celery notifications when issues are created or commented on.
- Add automatic access-token refresh in the frontend.
- Deploy Docker images to a hosting service and store uploaded files in object storage such as Amazon S3.
- Add more frontend tests and edge-case tests for billing.
