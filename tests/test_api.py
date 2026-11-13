import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from grading.models import Job, Outbox

pytestmark = pytest.mark.django_db


def payload(assignment, **extra):
    return {
        "assignment": assignment.pk,
        "source": "def normalize_labels():\n    return []",
        "idempotency_key": "example-1",
        **extra,
    }


def test_authentication():
    assert APIClient().get("/api/jobs/").status_code == 401


def test_jwt(user):
    client = APIClient()
    response = client.post(
        "/api/token/", {"username": user.username, "password": "synthetic-pass-42"}
    )
    assert response.status_code == 200
    client.credentials(HTTP_AUTHORIZATION="Bearer " + response.data["access"])
    assert client.get("/api/jobs/").status_code == 200


def test_invalid_jwt():
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Bearer invalid")
    assert client.get("/api/jobs/").status_code == 401


def test_submit_idempotency(client, assignment):
    first = client.post("/api/jobs/", payload(assignment), format="json")
    second = client.post("/api/jobs/", payload(assignment), format="json")
    assert first.status_code == 202 and second.status_code == 200
    assert first.data["id"] == second.data["id"]
    assert Job.objects.count() == Outbox.objects.count() == 1
    assert (
        client.post("/api/jobs/", payload(assignment, source="pass"), format="json").status_code
        == 409
    )


def test_owner_isolation(client, assignment):
    other = get_user_model().objects.create_user(username="other")
    assignment.owner = other
    assignment.save()
    assert client.get(f"/api/assignments/{assignment.pk}/").status_code == 404
    assert client.post("/api/jobs/", payload(assignment), format="json").status_code == 404
    assert (
        client.patch(f"/api/assignments/{assignment.pk}/", {"title": "stolen"}).status_code == 404
    )


def test_job_isolation(client, assignment, user):
    response = client.post("/api/jobs/", payload(assignment), format="json")
    other_client = APIClient()
    other_client.force_authenticate(get_user_model().objects.create_user(username="another"))
    assert other_client.get(f"/api/jobs/{response.data['id']}/").status_code == 404


def test_validation_and_pagination(client, assignment):
    response = client.post("/api/jobs/", payload(assignment, source="x" * 20001), format="json")
    assert response.status_code == 400 and "error" in response.data
    assert "results" in client.get("/api/jobs/?state=PENDING").data
    assert (
        client.post(
            "/api/assignments/", {"title": "x", "description": "y", "rubric": []}, format="json"
        ).status_code
        == 400
    )


def test_snapshot(client, assignment):
    client.post("/api/jobs/", payload(assignment), format="json")
    assignment.rubric = []
    assignment.save()
    assert len(Job.objects.get().rubric_snapshot) == 4


def test_health():
    assert APIClient().get("/health/").status_code == 200


def test_assignment_management(client, assignment):
    response = client.post(
        "/api/assignments/",
        {
            "title": "Syntax",
            "description": "Synthetic",
            "rubric": [{"kind": "syntax", "points": 100}],
        },
        format="json",
    )
    assert response.status_code == 201
    assert (
        client.patch(f"/api/assignments/{assignment.pk}/", {"title": "Updated"}).status_code == 200
    )
