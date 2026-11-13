import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-key-never-use-for-deployment-1234567890")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
from .settings import *  # noqa: F403

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
CELERY_TASK_ALWAYS_EAGER = True
