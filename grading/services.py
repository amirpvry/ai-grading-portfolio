from django.db import transaction
from rest_framework.exceptions import APIException

from grading.models import Job, JobEvent, Outbox


class Conflict(APIException):
    status_code = 409
    default_detail = "Idempotency key already used for a different request"


def submit(owner, assignment, source, key):
    # Serializing on the user makes concurrent first-use requests deterministic.
    with transaction.atomic():
        type(owner).objects.select_for_update().get(pk=owner.pk)
        assignment = type(assignment).objects.select_for_update().get(pk=assignment.pk)
        existing = Job.objects.filter(owner=owner, idempotency_key=key).first()
        if existing:
            if existing.assignment_id != assignment.pk or existing.source != source:
                raise Conflict()
            return existing, False
        job = Job.objects.create(
            owner=owner,
            assignment=assignment,
            source=source,
            rubric_snapshot=assignment.rubric,
            idempotency_key=key,
        )
        JobEvent.objects.create(job=job, state=job.state, reason="submitted")
        Outbox.objects.create(job=job)
        return job, True
