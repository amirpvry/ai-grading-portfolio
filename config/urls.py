from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from grading.api.views import AssignmentViewSet, HealthView, JobViewSet

router = DefaultRouter()
router.register("assignments", AssignmentViewSet, basename="assignment")
router.register("jobs", JobViewSet, basename="job")
urlpatterns = [
    path("api/", include(router.urls)),
    path("api/token/", TokenObtainPairView.as_view()),
    path("api/token/refresh/", TokenRefreshView.as_view()),
    path("health/", HealthView.as_view()),
]
