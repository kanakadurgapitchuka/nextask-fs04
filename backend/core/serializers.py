from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Workspace, Membership, Project, Board, WorkflowStatus, Sprint, Issue, Comment, Attachment, AuditEvent
User=get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password=serializers.CharField(write_only=True, min_length=8)
    class Meta:
        model=User; fields=("id","username","email","password")
    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

class WorkspaceSerializer(serializers.ModelSerializer):
    role=serializers.SerializerMethodField()
    class Meta: model=Workspace; fields=("id","name","slug","plan","subscription_status","created_at","role")
    def get_role(self,obj):
        req=self.context.get("request")
        m=Membership.objects.filter(workspace=obj,user=req.user).first() if req else None
        return m.role if m else None

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = "__all__"
        read_only_fields = ("workspace", "created_at")

    def create(self, validated_data):
        workspace = validated_data["workspace"]
        name = validated_data["name"]

        base_key = validated_data.get("key") or name.upper()
        base_key = "".join(
            char for char in base_key if char.isalnum()
        )[:12] or "TASK"

        key = base_key
        counter = 1

        while Project.objects.filter(
            workspace=workspace,
            key=key
        ).exists():
            suffix = str(counter)
            key = base_key[:12 - len(suffix)] + suffix
            counter += 1

        validated_data["key"] = key
        return super().create(validated_data)
class BoardSerializer(serializers.ModelSerializer):
    class Meta: model=Board; fields="__all__"; read_only_fields=("workspace","created_at")
class WorkflowStatusSerializer(serializers.ModelSerializer):
    class Meta: model=WorkflowStatus; fields="__all__"; read_only_fields=("workspace",)
class SprintSerializer(serializers.ModelSerializer):
    class Meta: model=Sprint; fields="__all__"; read_only_fields=("workspace",)
class IssueSerializer(serializers.ModelSerializer):
    status_name=serializers.CharField(source="status.name", read_only=True)
    class Meta: model=Issue; fields="__all__"; read_only_fields=("workspace","reporter","created_at","updated_at")
class CommentSerializer(serializers.ModelSerializer):
    class Meta: model=Comment; fields=("id","issue","body","author","created_at"); read_only_fields=("author","created_at")
class AttachmentSerializer(serializers.ModelSerializer):
    class Meta: model=Attachment; fields="__all__"; read_only_fields=("workspace","uploaded_by","uploaded_at")
class AuditEventSerializer(serializers.ModelSerializer):
    class Meta: model=AuditEvent; fields="__all__"
