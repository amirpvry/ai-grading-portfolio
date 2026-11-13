from rest_framework import serializers

from grading.domain.grader import validate_rubric
from grading.models import Assignment, Job, JobEvent


class AssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = ["id", "title", "description", "rubric", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]

    def validate_rubric(self, value):
        try:
            return validate_rubric(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc


class SubmissionSerializer(serializers.Serializer):
    assignment = serializers.IntegerField(min_value=1)
    source = serializers.CharField(max_length=20000, trim_whitespace=False)
    idempotency_key = serializers.RegexField(r"^[A-Za-z0-9_-]{1,100}$")

    def validate_source(self, value):
        if len(value.encode()) > 20000 or "\x00" in value:
            raise serializers.ValidationError(
                "Source must be at most 20000 bytes without null bytes"
            )
        return value


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobEvent
        fields = ["state", "reason", "created_at"]


class JobSerializer(serializers.ModelSerializer):
    history = EventSerializer(many=True, read_only=True)

    class Meta:
        model = Job
        fields = [
            "id",
            "assignment",
            "state",
            "result",
            "attempts",
            "created_at",
            "updated_at",
            "history",
        ]
