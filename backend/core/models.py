from django.conf import settings
from django.db import models
from django.utils.text import slugify

class Workspace(models.Model):
    name = models.CharField(max_length=140)
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="owned_workspaces")
    plan = models.CharField(max_length=20, default="FREE")
    stripe_customer_id = models.CharField(max_length=120, blank=True)
    stripe_subscription_id = models.CharField(max_length=120, blank=True)
    subscription_status = models.CharField(max_length=30, default="inactive")
    created_at = models.DateTimeField(auto_now_add=True)
    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:130] or "workspace"
            self.slug = f"{base}-{Workspace.objects.filter(slug__startswith=base).count()+1}"
        super().save(*args, **kwargs)
    def __str__(self): return self.name

class Membership(models.Model):
    OWNER="OWNER"; ADMIN="ADMIN"; MEMBER="MEMBER"; VIEWER="VIEWER"
    ROLES=[(OWNER,"Owner"),(ADMIN,"Admin"),(MEMBER,"Member"),(VIEWER,"Viewer")]
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="workspace_memberships")
    role = models.CharField(max_length=10, choices=ROLES, default=MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ("workspace","user")

class Project(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="projects")
    name = models.CharField(max_length=160)
    key = models.CharField(max_length=12)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ("workspace","key")
    def __str__(self): return f"{self.key}: {self.name}"

class Board(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="boards")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="boards")
    name = models.CharField(max_length=140, default="Main Board")
    created_at = models.DateTimeField(auto_now_add=True)

class WorkflowStatus(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="workflow_statuses")
    name = models.CharField(max_length=60)
    order = models.PositiveSmallIntegerField(default=0)
    color = models.CharField(max_length=20, default="#64748b")
    class Meta:
        ordering = ["order"]
        unique_together = ("workspace","name")

class Sprint(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="sprints")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="sprints")
    name = models.CharField(max_length=120)
    goal = models.TextField(blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=False)

class Issue(models.Model):
    PRIORITIES=[("LOW","Low"),("MEDIUM","Medium"),("HIGH","High"),("URGENT","Urgent")]
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="issues")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="issues")
    board = models.ForeignKey(Board, on_delete=models.SET_NULL, null=True, blank=True, related_name="issues")
    sprint = models.ForeignKey(Sprint, on_delete=models.SET_NULL, null=True, blank=True, related_name="issues")
    title = models.CharField(max_length=220)
    description = models.TextField(blank=True)
    status = models.ForeignKey(WorkflowStatus, on_delete=models.PROTECT, related_name="issues")
    priority = models.CharField(max_length=10, choices=PRIORITIES, default="MEDIUM")
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_issues")
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="reported_issues")
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Comment(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="comments")
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class Attachment(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="attachments")
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name="attachments")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    file = models.FileField(upload_to="issue_attachments/%Y/%m/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

class AuditEvent(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="audit_events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=80)
    entity_id = models.PositiveIntegerField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ["-created_at"]
