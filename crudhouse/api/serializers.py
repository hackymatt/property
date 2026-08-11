from django.db import transaction
from rest_framework import serializers
from domain.models import Domain
from scraper_source.models import ScraperSource, ScraperSourceStage
from job.models import Job, JobRunLog
from schedule.models import Schedule, ScheduleRunLog


class DomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = Domain
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class ScraperSourceStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScraperSourceStage
        fields = ("id", "stage_name", "order", "code_ref")
        read_only_fields = ("id",)


class ScraperSourceSerializer(serializers.ModelSerializer):
    domain_name = serializers.CharField(source="domain.name", read_only=True)
    stages = ScraperSourceStageSerializer(many=True, required=False)

    class Meta:
        model = ScraperSource
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")

    def _replace_stages(self, source, stages_data):
        """Stages are edited as one ordered list in the UI, so a write
        replaces the whole set rather than diffing individual rows. Safe
        because ScraperSourceStage holds only configuration — no run history
        points at it."""
        source.stages.all().delete()
        ScraperSourceStage.objects.bulk_create(
            [ScraperSourceStage(source=source, **stage) for stage in stages_data]
        )

    @transaction.atomic
    def create(self, validated_data):
        stages_data = validated_data.pop("stages", [])
        source = super().create(validated_data)
        self._replace_stages(source, stages_data)
        return source

    @transaction.atomic
    def update(self, instance, validated_data):
        stages_data = validated_data.pop("stages", None)
        source = super().update(instance, validated_data)
        if stages_data is not None:
            self._replace_stages(source, stages_data)
        return source


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
