import logging
import uuid
from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from grading.domain.grader import grade
from grading.infrastructure.feedback import get_provider
from grading.models import Job, JobEvent, Outbox

logger = logging.getLogger(__name__)


@shared_task
def dispatch():
    # Publish before marking: a crash may duplicate delivery, never lose the intent.
    for item in Outbox.objects.filter(sent_at__isnull=True)[:100]:
        run_job.delay(str(item.job_id))
        Outbox.objects.filter(pk=item.pk).update(sent_at=timezone.now())
    recoverable = Job.objects.filter(
        Q(state="PENDING") | Q(state="RUNNING", lease_until__lt=timezone.now())
    )
    for job_id in recoverable.values_list("pk", flat=True)[:100]:
        run_job.delay(str(job_id))


@shared_task(bind=True, max_retries=2)
def run_job(self, job_id):
    token = uuid.uuid4()
    with transaction.atomic():
        job = Job.objects.select_for_update().get(pk=job_id)
        if job.state in {"COMPLETED", "FAILED"}:
            return
        if job.state == "RUNNING" and job.lease_until > timezone.now():
            return
        if job.attempts >= 3:
            job.state = "FAILED"
            job.save(update_fields=["state", "updated_at"])
            JobEvent.objects.create(job=job, state="FAILED", reason="attempt_limit")
            return
        job.state, job.lease_token = "RUNNING", token
        job.lease_until = timezone.now() + timedelta(seconds=90)
        job.attempts += 1
        job.save()
        JobEvent.objects.create(job=job, state="RUNNING", reason="claimed")
    try:
        result = grade(job.source, job.rubric_snapshot)
        try:
            result["advisory"] = get_provider().feedback(job.source, result).model_dump()
        except Exception:
            result["advisory"] = {"status": "unavailable"}
            logger.warning("feedback_unavailable")
    except Exception as exc:
        with transaction.atomic():
            locked = Job.objects.select_for_update().get(pk=job_id)
            if locked.lease_token != token:
                return
            locked.state = "FAILED" if locked.attempts >= 3 else "PENDING"
            locked.save(update_fields=["state", "updated_at"])
            JobEvent.objects.create(job=locked, state=locked.state, reason="grading_error")
        if locked.state == "PENDING":
            raise self.retry(
                exc=RuntimeError("grading_error"), countdown=2**locked.attempts
            ) from exc
        return
    with transaction.atomic():
        locked = Job.objects.select_for_update().get(pk=job_id)
        if locked.lease_token != token:
            return
        locked.state, locked.result = "COMPLETED", result
        locked.save(update_fields=["state", "result", "updated_at"])
        JobEvent.objects.create(job=locked, state="COMPLETED", reason="graded")
    logger.info("grading_completed job_id=%s", job_id)
