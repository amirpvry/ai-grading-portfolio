import uuid

from django.conf import settings
from django.db import models


class Assignment(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(max_length=5000)
    rubric = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Job(models.Model):
    class State(models.TextChoices):
        PENDING = "PENDING"
        RUNNING = "RUNNING"
        COMPLETED = "COMPLETED"
        FAILED = "FAILED"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    assignment = models.ForeignKey(Assignment, on_delete=models.PROTECT)
    source = models.TextField()
    rubric_snapshot = models.JSONField()
    idempotency_key = models.CharField(max_length=100)
    state = models.CharField(max_length=10, choices=State, default=State.PENDING)
    result = models.JSONField(default=dict)
    attempts = models.PositiveIntegerField(default=0)
    lease_token = models.UUIDField(null=True)
    lease_until = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["owner", "idempotency_key"], name="owner_idempotency")
        ]
        indexes = [models.Index(fields=["state", "lease_until"])]


class JobEvent(models.Model):
    job = models.ForeignKey(Job, related_name="history", on_delete=models.CASCADE)
    state = models.CharField(max_length=10)
    reason = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)


class Outbox(models.Model):
    job = models.OneToOneField(Job, on_delete=models.CASCADE)
    sent_at = models.DateTimeField(null=True)
