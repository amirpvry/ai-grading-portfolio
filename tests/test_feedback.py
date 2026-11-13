from unittest.mock import patch

import httpx
import pytest

from grading.infrastructure.feedback import OpenAIProvider


def test_external_feedback_retries_timeout(settings, monkeypatch):
    settings.LLM_SEND_CODE_CONSENT = True
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-value")
    monkeypatch.setenv("OPENAI_MODEL", "synthetic-model")
    response = httpx.Response(
        200,
        request=httpx.Request("POST", "https://api.openai.com"),
        json={"choices": [{"message": {"content": '{"summary":"Advice","suggestions":[]}'}}]},
    )
    with patch("httpx.Client.post", side_effect=[httpx.ReadTimeout("timeout"), response]) as post:
        with patch("time.sleep"):
            assert OpenAIProvider().feedback("pass", {}).summary == "Advice"
        assert post.call_count == 2


def test_external_feedback_rejects_invalid_schema(settings, monkeypatch):
    settings.LLM_SEND_CODE_CONSENT = True
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-value")
    monkeypatch.setenv("OPENAI_MODEL", "synthetic-model")
    response = httpx.Response(
        200,
        request=httpx.Request("POST", "https://api.openai.com"),
        json={"choices": [{"message": {"content": '{"score":100}'}}]},
    )
    with patch("httpx.Client.post", return_value=response):
        with pytest.raises(ValueError):
            OpenAIProvider().feedback("pass", {})
