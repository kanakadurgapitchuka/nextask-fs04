from django.contrib import admin

from .models import *

admin.site.register(
    [
        Workspace,
        Membership,
        Project,
        Board,
        WorkflowStatus,
        Sprint,
        Issue,
        Comment,
        Attachment,
        AuditEvent,
    ]
)
