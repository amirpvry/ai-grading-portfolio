import pytest

from grading.domain.grader import grade, validate_rubric
from grading.infrastructure.feedback import Feedback, OpenAIProvider


@pytest.mark.parametrize(
    "source,score", [("def f():\n return 1", 100), ("import os", 50), ("def ???", 0)]
)
def test_structural_scores(source, score):
    rubric = validate_rubric(
        [{"kind": "syntax", "points": 50}, {"kind": "function", "target": "f", "points": 50}]
    )
    assert grade(source, rubric)["score"] == score


@pytest.mark.parametrize(
    "rubric",
    [
        [],
        [{"kind": "execute", "points": 100}],
        [{"kind": "syntax", "points": 10}],
        [{"kind": "function", "points": 100, "target": "bad-name"}],
    ],
)
def test_rubric_validation(rubric):
    with pytest.raises(ValueError):
        validate_rubric(rubric)


def test_source_is_never_executed(tmp_path):
    marker = tmp_path / "unsafe"
    grade(
        f"open({str(marker)!r}, 'w').write('bad')",
        [{"kind": "syntax", "points": 100, "target": ""}],
    )
    assert not marker.exists()


def test_external_consent(settings):
    settings.LLM_SEND_CODE_CONSENT = False
    with pytest.raises(ValueError, match="consent"):
        OpenAIProvider().feedback("secret", {})


def test_feedback_cannot_contain_score():
    with pytest.raises(ValueError):
        Feedback(summary="x", suggestions=[], score=100)
