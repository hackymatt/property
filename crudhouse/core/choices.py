# Choice definitions for models
from shared.consts import PropertyType as _PropertyType
from shared.consts import SourceKind as _SourceKind
from shared.consts import Status

# NOTE: Job.stage / JobRunLog.stage are plain CharFields, not choices-restricted.
# The authoritative stage sequence for a given ScraperSource lives in
# ScraperSourceStage.stage_name (DB), which varies per source_kind — a single
# global closed enum here would have to be migrated every time a new source
# type is added, defeating the point of ScraperSourceStage.


class SourceKind:
    PORTAL_LISTING = _SourceKind.PORTAL_LISTING
    FILE_REGISTRY = _SourceKind.FILE_REGISTRY

    CHOICES = [
        (PORTAL_LISTING, "Portal listing"),
        (FILE_REGISTRY, "File registry"),
    ]


class PropertyType:
    APARTMENT = _PropertyType.APARTMENT
    HOUSE = _PropertyType.HOUSE
    LAND = _PropertyType.LAND
    COMMERCIAL = _PropertyType.COMMERCIAL

    CHOICES = [
        (APARTMENT, "Apartment"),
        (HOUSE, "House"),
        (LAND, "Land"),
        (COMMERCIAL, "Commercial"),
    ]


class ExecutionStatus:
    PENDING = Status.PENDING
    RUNNING = Status.RUNNING
    SUCCESS = Status.SUCCESS
    FAILED = Status.FAILED
    CANCELLED = Status.CANCELLED

    CHOICES = [
        (PENDING, "Pending"),
        (RUNNING, "Running"),
        (SUCCESS, "Success"),
        (FAILED, "Failed"),
        (CANCELLED, "Cancelled"),
    ]
