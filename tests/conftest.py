import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from grading.models import Assignment


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(username="synthetic", password="synthetic-pass-42")


@pytest.fixture
def client(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.fixture
def assignment(user):
    return Assignment.objects.create(
        owner=user,
        title="Normalize labels",
        description="Define normalize_labels with a docstring; do not import modules.",
        rubric=[
            {"kind": "syntax", "target": "", "points": 20},
            {"kind": "function", "target": "normalize_labels", "points": 40},
            {"kind": "docstring", "target": "normalize_labels", "points": 20},
            {"kind": "no_imports", "target": "", "points": 20},
        ],
    )
