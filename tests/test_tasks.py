from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import patch

import pytest
from celery.exceptions import Retry
from django.db import close_old_connections, connection, connections
from django.utils import timezone

from grading.models import Job, Outbox
from grading.services import submit
from grading.tasks import dispatch, run_job

pytestmark = pytest.mark.django_db


def create(user, assignment):
    return submit(
        user,
        assignment,
        'def normalize_labels():\n    "Normalize labels."\n    return []',
        "task-1",
    )[0]


def test_complete_and_duplicate(user, assignment):
    job = create(user, assignment)
    run_job.run(str(job.pk))
    run_job.run(str(job.pk))
    job.refresh_from_db()
    assert job.state == "COMPLETED" and job.result["score"] == 100
    assert job.attempts == 1
    assert list(job.history.values_list("state", flat=True)) == ["PENDING", "RUNNING", "COMPLETED"]


def test_lease_recovery(user, assignment):
    job = create(user, assignment)
    job.state = "RUNNING"
    job.lease_until = timezone.now() + timedelta(seconds=90)
    job.save()
    run_job.run(str(job.pk))
    job.refresh_from_db()
    assert job.attempts == 0
    job.lease_until = timezone.now() - timedelta(seconds=1)
    job.save()
    run_job.run(str(job.pk))
    job.refresh_from_db()
    assert job.state == "COMPLETED"


def test_feedback_failure_preserves_score(user, assignment):
    job = create(user, assignment)
    with patch("grading.tasks.get_provider", side_effect=RuntimeError()):
        run_job.run(str(job.pk))
    job.refresh_from_db()
    assert job.result["score"] == 100 and job.result["advisory"]["status"] == "unavailable"


def test_retry_then_terminal(user, assignment):
    job = create(user, assignment)
    with (
        patch("grading.tasks.grade", side_effect=RuntimeError("private")),
        patch.object(run_job, "retry", side_effect=Retry()),
    ):
        for _ in range(2):
            with pytest.raises(Retry):
                run_job.run(str(job.pk))
        run_job.run(str(job.pk))
    job.refresh_from_db()
    assert job.state == "FAILED" and job.attempts == 3
    assert "private" not in str(job.result)


def test_outbox_publish_failure(user, assignment):
    create(user, assignment)
    with patch("grading.tasks.run_job.delay", side_effect=ConnectionError):
        with pytest.raises(ConnectionError):
            dispatch.run()
    assert Outbox.objects.get().sent_at is None


@pytest.mark.django_db(transaction=True)
def test_concurrent_submission(user, assignment):
    if connection.vendor != "postgresql":
        pytest.skip("Requires PostgreSQL row locks")

    def work(_):
        close_old_connections()
        try:
            return submit(user, assignment, "pass", "race")[0].pk
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=4) as executor:
        ids = list(executor.map(work, range(4)))
    assert len(set(ids)) == 1 and Job.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_worker_claim(user, assignment):
    if connection.vendor != "postgresql":
        pytest.skip("Requires PostgreSQL row locks")
    job = create(user, assignment)

    def work(_):
        close_old_connections()
        try:
            run_job.run(str(job.pk))
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(work, range(4)))
    job.refresh_from_db()
    assert job.attempts == 1 and job.state == "COMPLETED"


def test_stale_attempt_cannot_overwrite_result(user, assignment):
    import uuid

    job = create(user, assignment)

    def newer_attempt(*args):
        Job.objects.filter(pk=job.pk).update(lease_token=uuid.uuid4(), result={"newer": True})
        return {"score": 100}

    with patch("grading.tasks.grade", side_effect=newer_attempt):
        run_job.run(str(job.pk))
    job.refresh_from_db()
    assert job.result == {"newer": True}
    assert not job.history.filter(state="COMPLETED").exists()


def test_abandoned_attempt_limit(user, assignment):
    job = create(user, assignment)
    job.attempts = 3
    job.save()
    run_job.run(str(job.pk))
    job.refresh_from_db()
    assert job.state == "FAILED"
    assert job.history.filter(reason="attempt_limit").exists()
