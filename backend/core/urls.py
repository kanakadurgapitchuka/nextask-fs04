from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import *

router = DefaultRouter()
router.register("workspaces", WorkspaceViewSet, basename="workspace")
router.register("projects", ProjectViewSet, basename="project")
router.register("boards", BoardViewSet, basename="board")
router.register("statuses", WorkflowStatusViewSet, basename="status")
router.register("sprints", SprintViewSet, basename="sprint")
router.register("issues", IssueViewSet, basename="issue")
router.register("comments", CommentViewSet, basename="comment")
router.register("attachments", AttachmentViewSet, basename="attachment")
router.register("audit-events", AuditEventViewSet, basename="audit")
urlpatterns = [
    path("auth/register/", RegisterView.as_view()),
    path("billing/checkout/", create_checkout),
    path("billing/webhook/", stripe_webhook),
    path("", include(router.urls)),
]
