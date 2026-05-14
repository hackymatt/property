from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DomainViewSet, ScraperSourceViewSet, JobViewSet, ScheduleViewSet, LoginView, JobRunLogViewSet, ScheduleRunLogViewSet

router = DefaultRouter(trailing_slash=False)
router.register("domains", DomainViewSet)
router.register("sources", ScraperSourceViewSet)
router.register("jobs", JobViewSet)
router.register("schedules", ScheduleViewSet)
router.register("run-logs", JobRunLogViewSet)
router.register("schedule-logs", ScheduleRunLogViewSet)

urlpatterns = [
    path("auth/login", LoginView.as_view()),
    path("", include(router.urls)),
]
