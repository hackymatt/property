from rest_framework import serializers
from domain.models import Domain
from scraper_source.models import ScraperSource
from job.models import Job, JobRunLog
from schedule.models import Schedule, ScheduleRunLog


class DomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = Domain
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class ScraperSourceSerializer(serializers.ModelSerializer):
    domain_name = serializers.CharField(source="domain.name", read_only=True)

    class Meta:
        model = ScraperSource
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class JobSerializer(serializers.ModelSerializer):
    domain_name = serializers.CharField(source="domain.name", read_only=True)

    class Meta:
        model = Job
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class ScheduleSerializer(serializers.ModelSerializer):
    jobs = serializers.PrimaryKeyRelatedField(
        queryset=Job.objects.all(), many=True, required=False
    )
    next_run = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Schedule
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "next_run")


class JobRunLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobRunLog
        fields = "__all__"


class ScheduleRunLogSerializer(serializers.ModelSerializer):
    schedule_name = serializers.CharField(source="schedule.name", read_only=True)

    class Meta:
        model = ScheduleRunLog
        fields = "__all__"
