import json, stripe
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from rest_framework import generics, viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.exceptions import PermissionDenied, APIException
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from .models import *
from .serializers import *
from .permissions import membership_for, WRITE_ROLES
from .tasks import build_workspace_report

User=get_user_model()

# Plan limits: None means unlimited
PLAN_LIMITS={"FREE":{"projects":3,"issues":10},"PRO":{"projects":None,"issues":None}}

class PlanLimitReached(APIException):
    status_code=402
    default_detail="Plan limit reached. Upgrade to Pro to add more."
    default_code="plan_limit"

def check_plan_limit(ws,kind):
    limit=PLAN_LIMITS.get(ws.plan,PLAN_LIMITS["FREE"])[kind]
    if limit is None: return
    count=ws.projects.count() if kind=="projects" else ws.issues.count()
    if count>=limit:
        raise PlanLimitReached(f"Free plan allows {limit} {kind}. Upgrade to Pro to add more.")

@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    return Response({"ok": True, "service": "nextask-api"})

class RegisterView(generics.CreateAPIView):
    queryset=User.objects.all(); serializer_class=RegisterSerializer; permission_classes=[AllowAny]

class WorkspaceViewSet(viewsets.ModelViewSet):
    serializer_class=WorkspaceSerializer
    def get_queryset(self): return Workspace.objects.filter(memberships__user=self.request.user).distinct()
    def perform_create(self, serializer):
        with transaction.atomic():
            ws=serializer.save(created_by=self.request.user)
            Membership.objects.create(workspace=ws,user=self.request.user,role=Membership.OWNER)
            for i,name in enumerate(["To Do","In Progress","Done"]):
                WorkflowStatus.objects.create(workspace=ws,name=name,order=i)
            AuditEvent.objects.create(workspace=ws,actor=self.request.user,action="workspace.created",entity_type="Workspace",entity_id=ws.id)
    @action(detail=True,methods=["post"])
    def report(self,request,pk=None):
        ws=self.get_object()
        m=membership_for(request.user,ws.id)
        if not m or m.role not in (Membership.OWNER,Membership.ADMIN):
            raise PermissionDenied("Only workspace owner/admin can generate reports.")
        task=build_workspace_report.delay(ws.id)
        AuditEvent.objects.create(workspace=ws,actor=request.user,action="report.requested",entity_type="Workspace",entity_id=ws.id,metadata={"task_id":task.id})
        return Response({"task_id":task.id,"status":"queued"},status=202)

class TenantViewSet(viewsets.ModelViewSet):
    def get_workspace(self):
        wid=self.request.data.get("workspace") or self.request.query_params.get("workspace")
        if not wid and self.action in ("retrieve","update","partial_update","destroy"):
            obj=self.get_object(); wid=obj.workspace_id
        m=membership_for(self.request.user,wid) if wid else None
        if not m: return None
        return m.workspace
    def ensure_can_write(self, workspace_id):
        m = membership_for(self.request.user, workspace_id)
        if not m or m.role not in WRITE_ROLES:
            raise PermissionDenied("Your role does not allow this action.")
    def get_queryset(self):
        qs=self.queryset.filter(workspace__memberships__user=self.request.user).distinct()
        wid=self.request.query_params.get("workspace")
        if wid and str(wid).isdigit():
            qs=qs.filter(workspace_id=int(wid))
        return qs
    def perform_create(self, serializer):
        ws=self.get_workspace()
        if not ws: raise PermissionDenied("You must be a member of the selected workspace.")
        self.ensure_can_write(ws.id)
        obj=serializer.save(workspace=ws)
        AuditEvent.objects.create(workspace=ws,actor=self.request.user,action=f"{obj.__class__.__name__.lower()}.created",entity_type=obj.__class__.__name__,entity_id=obj.id)
    def perform_update(self, serializer):
        self.ensure_can_write(serializer.instance.workspace_id)
        obj=serializer.save()
        AuditEvent.objects.create(workspace=obj.workspace,actor=self.request.user,action=f"{obj.__class__.__name__.lower()}.updated",entity_type=obj.__class__.__name__,entity_id=obj.id)
    def perform_destroy(self, instance):
        self.ensure_can_write(instance.workspace_id)
        instance.delete()

class ProjectViewSet(TenantViewSet):
    queryset=Project.objects.all(); serializer_class=ProjectSerializer
    def perform_create(self, serializer):
        ws=self.get_workspace()
        if not ws: raise PermissionDenied("You must be a member of the selected workspace.")
        self.ensure_can_write(ws.id)
        check_plan_limit(ws,"projects")
        # Auto-generate a unique key inside this workspace (STUDEN, STUDEN2, STUDEN3 ...)
        base=(serializer.validated_data.get("key") or "TASK")[:8]
        key=base; n=2
        while Project.objects.filter(workspace=ws,key=key).exists():
            key=f"{base}{n}"; n+=1
        obj=serializer.save(workspace=ws,key=key)
        AuditEvent.objects.create(workspace=ws,actor=self.request.user,action="project.created",entity_type="Project",entity_id=obj.id)
class BoardViewSet(TenantViewSet):
    queryset=Board.objects.select_related("project").all(); serializer_class=BoardSerializer
class WorkflowStatusViewSet(TenantViewSet):
    queryset=WorkflowStatus.objects.all(); serializer_class=WorkflowStatusSerializer
class SprintViewSet(TenantViewSet):
    queryset=Sprint.objects.all(); serializer_class=SprintSerializer
class IssueViewSet(TenantViewSet):
    queryset=Issue.objects.select_related("status","project","assignee").all(); serializer_class=IssueSerializer
    def perform_create(self, serializer):
        ws=self.get_workspace()
        if not ws: raise PermissionDenied("Workspace membership required.")
        self.ensure_can_write(ws.id)
        check_plan_limit(ws,"issues")
        obj=serializer.save(workspace=ws,reporter=self.request.user)
        AuditEvent.objects.create(workspace=ws,actor=self.request.user,action="issue.created",entity_type="Issue",entity_id=obj.id)
    @action(detail=True,methods=["patch"])
    def move(self,request,pk=None):
        issue=self.get_object()
        self.ensure_can_write(issue.workspace_id)
        status_obj=WorkflowStatus.objects.filter(id=request.data.get("status"),workspace=issue.workspace).first()
        if not status_obj: return Response({"detail":"Invalid status for this workspace."},status=400)
        old=issue.status.name; issue.status=status_obj; issue.save()
        AuditEvent.objects.create(workspace=issue.workspace,actor=request.user,action="issue.moved",entity_type="Issue",entity_id=issue.id,metadata={"from":old,"to":status_obj.name})
        return Response(self.get_serializer(issue).data)

class CommentViewSet(viewsets.ModelViewSet):
    serializer_class=CommentSerializer
    def get_queryset(self): return Comment.objects.filter(workspace__memberships__user=self.request.user).distinct()
    def perform_create(self,serializer):
        issue=serializer.validated_data["issue"]
        if not Membership.objects.filter(workspace=issue.workspace,user=self.request.user).exists(): raise PermissionDenied("Workspace membership required.")
        serializer.save(workspace=issue.workspace,author=self.request.user)
        AuditEvent.objects.create(workspace=issue.workspace,actor=self.request.user,action="comment.created",entity_type="Issue",entity_id=issue.id)

class AttachmentViewSet(viewsets.ModelViewSet):
    serializer_class=AttachmentSerializer
    filterset_fields=["issue"]
    def get_queryset(self): return Attachment.objects.filter(workspace__memberships__user=self.request.user).distinct()
    def perform_create(self,serializer):
        issue=serializer.validated_data["issue"]
        m=membership_for(self.request.user,issue.workspace_id)
        if not m: raise PermissionDenied("Workspace membership required.")
        if m.role not in WRITE_ROLES: raise PermissionDenied("Your role does not allow this action.")
        obj=serializer.save(workspace=issue.workspace,uploaded_by=self.request.user)
        AuditEvent.objects.create(workspace=issue.workspace,actor=self.request.user,action="attachment.created",entity_type="Issue",entity_id=issue.id,metadata={"file":obj.file.name.split("/")[-1]})

class AuditEventViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class=AuditEventSerializer
    def get_queryset(self): return AuditEvent.objects.filter(workspace__memberships__user=self.request.user).distinct()

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_checkout(request):
    ws_id=request.data.get("workspace")
    membership=membership_for(request.user,ws_id)
    if not membership or membership.role not in (Membership.OWNER,Membership.ADMIN):
        return Response({"detail":"Workspace owner/admin permission required."},status=403)
    if not settings.STRIPE_SECRET_KEY or not settings.STRIPE_PRICE_ID:
        return Response({"detail":"Configure STRIPE_SECRET_KEY and STRIPE_PRICE_ID in environment."},status=503)
    stripe.api_key=settings.STRIPE_SECRET_KEY
    session=stripe.checkout.Session.create(
        mode="subscription", line_items=[{"price":settings.STRIPE_PRICE_ID,"quantity":1}],
        success_url=settings.FRONTEND_URL+"/?billing=success",cancel_url=settings.FRONTEND_URL+"/?billing=cancelled",
        metadata={"workspace_id":str(ws_id),"user_id":str(request.user.id)},
        subscription_data={"metadata":{"workspace_id":str(ws_id)}})
    return Response({"checkout_url":session.url})

@api_view(["POST"])
@permission_classes([AllowAny])
def stripe_webhook(request):
    try:
        event=stripe.Webhook.construct_event(request.body,request.headers.get("Stripe-Signature"),settings.STRIPE_WEBHOOK_SECRET)
    except Exception:
        return HttpResponse(status=400)
    if event["type"] in ("checkout.session.completed","customer.subscription.updated","customer.subscription.deleted"):
        obj=event["data"]["object"]
        ws_id=(obj.get("metadata") or {}).get("workspace_id")
        ws=Workspace.objects.filter(id=ws_id).first() if ws_id else None
        if not ws and event["type"].startswith("customer.subscription"):
            ws=Workspace.objects.filter(stripe_subscription_id=obj.get("id") or "").first()
        if ws:
            if event["type"]=="checkout.session.completed":
                ws.plan="PRO"; ws.subscription_status="active"
                ws.stripe_customer_id=obj.get("customer") or ""
                ws.stripe_subscription_id=obj.get("subscription") or ""
            elif event["type"]=="customer.subscription.deleted":
                ws.plan="FREE"; ws.subscription_status="cancelled"
            else:
                st=obj.get("status") or "active"
                ws.subscription_status=st
                ws.plan="PRO" if st in ("active","trialing") else "FREE"
            ws.save()
    return HttpResponse(status=200)