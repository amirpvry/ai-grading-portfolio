from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from grading.models import Assignment


class Command(BaseCommand):
    help = "Create an original synthetic assignment for an existing user"

    def add_arguments(self, parser):
        parser.add_argument("username")

    def handle(self, username, **options):
        user = get_user_model().objects.get(username=username)
        Assignment.objects.get_or_create(
            owner=user,
            title="Normalize labels",
            defaults={
                "description": (
                    "Write normalize_labels(values) to trim whitespace, lowercase labels "
                    "and omit empty strings. Runtime semantics are intentionally not graded "
                    "by this AST demonstration."
                ),
                "rubric": [
                    {"kind": "syntax", "target": "", "points": 20},
                    {"kind": "function", "target": "normalize_labels", "points": 40},
                    {"kind": "docstring", "target": "normalize_labels", "points": 20},
                    {"kind": "no_imports", "target": "", "points": 20},
                ],
            },
        )
        self.stdout.write("Synthetic assignment ready")
