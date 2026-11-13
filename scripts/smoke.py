"""Run against disposable local PostgreSQL/Redis; starts real service subprocesses."""

import logging
import os
import secrets
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import django
import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from django.contrib.auth import get_user_model  # noqa: E402

from grading.models import Assignment, Job  # noqa: E402


def main():
    logging.getLogger("httpx").setLevel(logging.WARNING)
    subprocess.run([sys.executable, "manage.py", "migrate", "--noinput"], cwd=ROOT, check=True)
    username, password = "smoke_" + secrets.token_hex(6), secrets.token_urlsafe(24)
    user = get_user_model().objects.create_user(username=username, password=password)
    commands = [
        [sys.executable, "-m", "gunicorn", "config.wsgi:application", "--bind", "127.0.0.1:18080"],
        [sys.executable, "-m", "celery", "-A", "config", "worker", "--concurrency=2"],
        [sys.executable, "-m", "celery", "-A", "config", "beat"],
    ]
    processes = []
    scratch = tempfile.TemporaryDirectory()
    try:
        with open("/tmp/portfolio-smoke.log", "w") as log:
            commands[2].append("--schedule=" + scratch.name + "/beat")
            for command in commands:
                processes.append(subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=log))
            with httpx.Client(
                base_url="http://localhost:18080", trust_env=False, timeout=5
            ) as client:
                for _ in range(50):
                    try:
                        if client.get("/health/").status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    time.sleep(0.2)
                else:
                    raise RuntimeError("API did not become healthy")
                token = client.post(
                    "/api/token/", json={"username": username, "password": password}
                )
                token.raise_for_status()
                client.headers["Authorization"] = "Bearer " + token.json()["access"]
                assignment = client.post(
                    "/api/assignments/",
                    json={
                        "title": "Synthetic smoke",
                        "description": "Structural syntax check",
                        "rubric": [{"kind": "syntax", "points": 100}],
                    },
                )
                assert assignment.status_code == 201
                payload = {
                    "assignment": assignment.json()["id"],
                    "source": "raise RuntimeError('never execute')",
                    "idempotency_key": "smoke-001",
                }
                submission = client.post("/api/jobs/", json=payload)
                assert submission.status_code == 202
                job_id = submission.json()["id"]
                for _ in range(100):
                    detail = client.get(f"/api/jobs/{job_id}/").json()
                    if detail["state"] in {"COMPLETED", "FAILED"}:
                        break
                    time.sleep(0.3)
                assert detail["state"] == "COMPLETED", detail
                assert detail["result"]["score"] == 100
                assert [row["state"] for row in detail["history"]] == [
                    "PENDING",
                    "RUNNING",
                    "COMPLETED",
                ]
                assert client.post("/api/jobs/", json=payload).status_code == 200
                print("PASS: JWT -> HTTP -> outbox/Beat -> Redis -> Celery -> score/history/replay")
    finally:
        for process in processes:
            process.terminate()
        for process in processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        Job.objects.filter(owner=user).delete()
        Assignment.objects.filter(owner=user).delete()
        user.delete()
        scratch.cleanup()


if __name__ == "__main__":
    main()
