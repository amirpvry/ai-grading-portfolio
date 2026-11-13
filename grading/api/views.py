from django.db import connection
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from grading.api.serializers import AssignmentSerializer, JobSerializer, SubmissionSerializer
from grading.models import Assignment, Job
from grading.services import submit


class AssignmentViewSet(viewsets.ModelViewSet):
    serializer_class = AssignmentSerializer
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    def get_queryset(self):
        return Assignment.objects.filter(owner=self.request.user).order_by("-id")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class JobViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = JobSerializer

    def get_queryset(self):
        qs = (
            Job.objects.filter(owner=self.request.user)
            .prefetch_related("history")
            .order_by("-created_at")
        )
        state = self.request.query_params.get("state")
        if state:
            qs = qs.filter(state=state)
        return qs

    def create(self, request):
        serializer = SubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        assignment = get_object_or_404(Assignment, pk=data["assignment"], owner=request.user)
        job, created = submit(request.user, assignment, data["source"], data["idempotency_key"])
        return Response(
            JobSerializer(job).data, status=status.HTTP_202_ACCEPTED if created else 200
        )


class HealthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception:
            return Response({"status": "unavailable"}, status=503)
        return Response({"status": "ok"})
