from rest_framework.permissions import BasePermission

from .models import Membership

WRITE_ROLES = [Membership.OWNER, Membership.ADMIN, Membership.MEMBER]
ADMIN_ROLES = [Membership.OWNER, Membership.ADMIN]


def membership_for(user, workspace_id):
    if not user or not user.is_authenticated:
        return None
    return (
        Membership.objects.filter(user=user, workspace_id=workspace_id)
        .select_related("workspace")
        .first()
    )


class IsWorkspaceMember(BasePermission):
    def has_object_permission(self, request, view, obj):
        workspace_id = getattr(obj, "workspace_id", None)
        return bool(workspace_id and membership_for(request.user, workspace_id))


class CanManageWorkspace(BasePermission):
    def has_permission(self, request, view):
        workspace_id = request.data.get("workspace") or request.query_params.get(
            "workspace"
        )
        if not workspace_id:
            return False
        m = membership_for(request.user, workspace_id)
        return bool(m and m.role in ADMIN_ROLES)
