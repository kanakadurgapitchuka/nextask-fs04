from celery import shared_task
from django.core.mail import send_mail


@shared_task
def send_workspace_notification(subject, message, recipient):
    # Configure EMAIL_* settings before using a real mail provider.
    return send_mail(subject, message, None, [recipient], fail_silently=True)


@shared_task
def build_workspace_report(workspace_id):
    from .models import Issue

    return {
        "workspace_id": workspace_id,
        "issue_count": Issue.objects.filter(workspace_id=workspace_id).count(),
    }
