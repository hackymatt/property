from rest_framework import viewsets, filters
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from domain.models import Domain
from scraper_source.models import ScraperSource
from job.models import Job, JobRunLog
from schedule.models import Schedule, ScheduleRunLog
from .serializers import (
    DomainSerializer,
    ScraperSourceSerializer,
    JobSerializer,
    ScheduleSerializer,
    JobRunLogSerializer,
    ScheduleRunLogSerializer,
)


class LoginView(ObtainAuthToken):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "username": user.username})


class DomainViewSet(viewsets.ModelViewSet):
    queryset = Domain.objects.all().order_by("name")
    serializer_class = DomainSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering_fields = "__all__"


class ScraperSourceViewSet(viewsets.ModelViewSet):
    queryset = ScraperSource.objects.select_related("domain").order_by("name")
    serializer_class = ScraperSourceSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "domain__name", "offer_url_prefix"]
    ordering_fields = "__all__"


class JobViewSet(viewsets.ModelViewSet):
    queryset = Job.objects.select_related("domain").order_by("-created_at")
    serializer_class = JobSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "source", "stage", "domain__name", "url"]
    ordering_fields = "__all__"


class ScheduleViewSet(viewsets.ModelViewSet):
    queryset = Schedule.objects.prefetch_related("jobs").order_by("name")
    serializer_class = ScheduleSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "cron"]
    ordering_fields = "__all__"


class JobRunLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = JobRunLog.objects.all().order_by("-created_at")
    serializer_class = JobRunLogSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["source", "stage", "domain_name", "status", "url"]
    ordering_fields = "__all__"


class ScheduleRunLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ScheduleRunLog.objects.select_related("schedule").order_by("-created_at")
    serializer_class = ScheduleRunLogSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["schedule__name", "status"]
    ordering_fields = "__all__"
