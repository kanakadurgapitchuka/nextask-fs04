from unittest.mock import patch
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Workspace, Membership, WorkflowStatus, Project, Issue, Sprint

User=get_user_model()
class TenantIsolationTests(TestCase):
    def setUp(self):
        self.a=User.objects.create_user(username="alice",password="StrongPass123!")
        self.b=User.objects.create_user(username="bob",password="StrongPass123!")
        self.wa=Workspace.objects.create(name="Alpha",created_by=self.a)
        self.wb=Workspace.objects.create(name="Beta",created_by=self.b)
        Membership.objects.create(workspace=self.wa,user=self.a,role="OWNER")
        Membership.objects.create(workspace=self.wb,user=self.b,role="OWNER")
        self.client=APIClient()
    def auth(self,user):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer "+str(RefreshToken.for_user(user).access_token))
    def test_user_only_sees_own_workspaces(self):
        self.auth(self.a)
        response=self.client.get("/api/workspaces/")
        self.assertEqual(response.status_code,200)
        ids=[x["id"] for x in response.data]
        self.assertIn(self.wa.id,ids); self.assertNotIn(self.wb.id,ids)
    def test_workspace_create_adds_owner_and_default_statuses(self):
        self.auth(self.a)
        response=self.client.post("/api/workspaces/",{"name":"Gamma"},format="json")
        self.assertEqual(response.status_code,201)
        ws_id=response.data["id"]
        self.assertTrue(Membership.objects.filter(workspace_id=ws_id,user=self.a,role="OWNER").exists())
        self.assertEqual(WorkflowStatus.objects.filter(workspace_id=ws_id).count(),3)
    def test_cannot_create_project_in_another_workspace(self):
        self.auth(self.a)
        response = self.client.post(
            "/api/projects/",
            {"workspace": self.wb.id, "name": "Intruder", "key": "HACK"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Project.objects.filter(key="HACK").exists())
    def test_viewer_cannot_create_project(self):
        viewer = User.objects.create_user(username="carol", password="StrongPass123!")
        Membership.objects.create(workspace=self.wa, user=viewer, role="VIEWER")
        self.auth(viewer)
        response = self.client.post(
            "/api/projects/",
            {"workspace": self.wa.id, "name": "Nope", "key": "NOPE"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Project.objects.filter(key="NOPE").exists())

    def test_free_plan_limits_projects_and_pro_is_unlimited(self):
        self.auth(self.a)
        for i in range(3):
            r=self.client.post("/api/projects/",{"workspace":self.wa.id,"name":f"P{i}","key":"PRJ"},format="json")
            self.assertEqual(r.status_code,201)
        r=self.client.post("/api/projects/",{"workspace":self.wa.id,"name":"P4","key":"PRJ"},format="json")
        self.assertEqual(r.status_code,402)
        self.wa.plan="PRO"; self.wa.save()
        r=self.client.post("/api/projects/",{"workspace":self.wa.id,"name":"P5","key":"PRJ"},format="json")
        self.assertEqual(r.status_code,201)
    def test_webhook_upgrades_workspace_to_pro(self):
        event={"type":"checkout.session.completed","data":{"object":{
            "metadata":{"workspace_id":str(self.wa.id)},"customer":"cus_test","subscription":"sub_test"}}}
        with patch("core.views.stripe.Webhook.construct_event",return_value=event):
            r=self.client.post("/api/billing/webhook/",data=b"{}",content_type="application/json",HTTP_STRIPE_SIGNATURE="x")
        self.assertEqual(r.status_code,200)
        self.wa.refresh_from_db()
        self.assertEqual(self.wa.plan,"PRO")
        self.assertEqual(self.wa.subscription_status,"active")
        self.assertEqual(self.wa.stripe_customer_id,"cus_test")

    def _issue_in_alpha(self):
        pa=Project.objects.create(workspace=self.wa,name="PA",key="PA")
        sa=WorkflowStatus.objects.create(workspace=self.wa,name="To Do",order=0)
        issue=Issue.objects.create(workspace=self.wa,project=pa,title="T",status=sa,reporter=self.a)
        return pa,issue
    def test_sprint_create_and_assign_issue(self):
        pa,issue=self._issue_in_alpha()
        self.auth(self.a)
        r=self.client.post("/api/sprints/",{"workspace":self.wa.id,"project":pa.id,"name":"Sprint 1"},format="json")
        self.assertEqual(r.status_code,201)
        r2=self.client.patch(f"/api/issues/{issue.id}/",{"sprint":r.data["id"]},format="json")
        self.assertEqual(r2.status_code,200)
        issue.refresh_from_db()
        self.assertEqual(issue.sprint_id,r.data["id"])
    def test_cannot_assign_issue_to_other_workspace_sprint(self):
        pa,issue=self._issue_in_alpha()
        pb=Project.objects.create(workspace=self.wb,name="PB",key="PB")
        sprint_b=Sprint.objects.create(workspace=self.wb,project=pb,name="Beta sprint")
        self.auth(self.a)
        r=self.client.patch(f"/api/issues/{issue.id}/",{"sprint":sprint_b.id},format="json")
        self.assertEqual(r.status_code,403)
        issue.refresh_from_db()
        self.assertIsNone(issue.sprint)

    def test_owner_adds_viewer_and_viewer_is_read_only(self):
        viewer=User.objects.create_user(username="vera",password="StrongPass123!")
        self.auth(self.a)
        r=self.client.post(f"/api/workspaces/{self.wa.id}/members/",{"username":"vera","role":"VIEWER"},format="json")
        self.assertEqual(r.status_code,201)
        self.assertTrue(Membership.objects.filter(workspace=self.wa,user=viewer,role="VIEWER").exists())
        self.auth(viewer)
        r2=self.client.post("/api/projects/",{"workspace":self.wa.id,"name":"X","key":"X"},format="json")
        self.assertEqual(r2.status_code,403)
    def test_member_cannot_manage_members(self):
        member=User.objects.create_user(username="mike",password="StrongPass123!")
        User.objects.create_user(username="nina",password="StrongPass123!")
        Membership.objects.create(workspace=self.wa,user=member,role="MEMBER")
        self.auth(member)
        r=self.client.post(f"/api/workspaces/{self.wa.id}/members/",{"username":"nina","role":"VIEWER"},format="json")
        self.assertEqual(r.status_code,403)
    def test_add_unknown_user_returns_404(self):
        self.auth(self.a)
        r=self.client.post(f"/api/workspaces/{self.wa.id}/members/",{"username":"nobody","role":"VIEWER"},format="json")
        self.assertEqual(r.status_code,404)