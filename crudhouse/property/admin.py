from django.contrib import admin


from import_export import resources
from import_export.admin import ImportExportModelAdmin

from .models import (
    Location,
    AdvertiserType,
    AdvertiserName,
    DevelopmentName,
    MarketType,
    TransactionType,
    PropertyType,
    Room,
    Floor,
    BuildingFloor,
    ConstructionStatus,
    BuildingType,
    BuildingMaterial,
    HeatingType,
    OwnershipType,
    ApartmentListing,
    ApartmentListingChange,
)


class LocationResource(resources.ModelResource):
    class Meta:
        model = Location


class AdvertiserTypeResource(resources.ModelResource):
    class Meta:
        model = AdvertiserType


class AdvertiserNameResource(resources.ModelResource):
    class Meta:
        model = AdvertiserName


class DevelopmentNameResource(resources.ModelResource):
    class Meta:
        model = DevelopmentName


class MarketTypeResource(resources.ModelResource):
    class Meta:
        model = MarketType


class TransactionTypeResource(resources.ModelResource):
    class Meta:
        model = TransactionType


class PropertyTypeResource(resources.ModelResource):
    class Meta:
        model = PropertyType


class RoomResource(resources.ModelResource):
    class Meta:
        model = Room


class FloorResource(resources.ModelResource):
    class Meta:
        model = Floor


class BuildingFloorResource(resources.ModelResource):
    class Meta:
        model = BuildingFloor


class ConstructionStatusResource(resources.ModelResource):
    class Meta:
        model = ConstructionStatus


class BuildingTypeResource(resources.ModelResource):
    class Meta:
        model = BuildingType


class BuildingMaterialResource(resources.ModelResource):
    class Meta:
        model = BuildingMaterial


class HeatingTypeResource(resources.ModelResource):
    class Meta:
        model = HeatingType


class OwnershipTypeResource(resources.ModelResource):
    class Meta:
        model = OwnershipType


class ApartmentListingResource(resources.ModelResource):
    class Meta:
        model = ApartmentListing


class ApartmentListingChangeResource(resources.ModelResource):
    class Meta:
        model = ApartmentListingChange


@admin.register(Location)
class LocationAdmin(ImportExportModelAdmin):
    resource_class = LocationResource
    list_display = (
        "city",
        "district",
        "subdistrict",
        "municipality",
        "county",
        "postal_code",
        "province",
        "street",
        "latitude",
        "longitude",
    )
    search_fields = (
        "city",
        "district",
        "subdistrict",
        "municipality",
        "county",
        "postal_code",
        "province",
        "street",
    )


@admin.register(AdvertiserType)
class AdvertiserTypeAdmin(ImportExportModelAdmin):
    resource_class = AdvertiserTypeResource
    list_display = ("name", "pl")
    search_fields = ("name", "pl")


@admin.register(AdvertiserName)
class AdvertiserNameAdmin(ImportExportModelAdmin):
    resource_class = AdvertiserNameResource
    list_display = ("name", "clean_name")
    search_fields = ("name", "clean_name")


@admin.register(DevelopmentName)
class DevelopmentNameAdmin(ImportExportModelAdmin):
    resource_class = DevelopmentNameResource
    list_display = ("name", "clean_name")
    search_fields = ("name", "clean_name")


@admin.register(MarketType)
class MarketTypeAdmin(ImportExportModelAdmin):
    resource_class = MarketTypeResource
    list_display = ("name", "pl")
    search_fields = ("name", "pl")


@admin.register(TransactionType)
class TransactionTypeAdmin(ImportExportModelAdmin):
    resource_class = TransactionTypeResource
    list_display = ("name", "pl")
    search_fields = ("name", "pl")


@admin.register(PropertyType)
class PropertyTypeAdmin(ImportExportModelAdmin):
    resource_class = PropertyTypeResource
    list_display = ("name", "pl")
    search_fields = ("name", "pl")


@admin.register(Room)
class RoomAdmin(ImportExportModelAdmin):
    resource_class = RoomResource
    list_display = ("name", "pl")
    search_fields = ("name", "pl")


@admin.register(Floor)
class FloorAdmin(ImportExportModelAdmin):
    resource_class = FloorResource
    list_display = ("name", "pl")
    search_fields = ("name", "pl")


@admin.register(BuildingFloor)
class BuildingFloorAdmin(ImportExportModelAdmin):
    resource_class = BuildingFloorResource
    list_display = ("name", "pl")
    search_fields = ("name", "pl")


@admin.register(ConstructionStatus)
class ConstructionStatusAdmin(ImportExportModelAdmin):
    resource_class = ConstructionStatusResource
    list_display = ("name", "pl")
    search_fields = ("name", "pl")


@admin.register(BuildingType)
class BuildingTypeAdmin(ImportExportModelAdmin):
    resource_class = BuildingTypeResource
    list_display = ("name", "pl")
    search_fields = ("name", "pl")


@admin.register(BuildingMaterial)
class BuildingMaterialAdmin(ImportExportModelAdmin):
    resource_class = BuildingMaterialResource
    list_display = ("name", "pl")
    search_fields = ("name", "pl")


@admin.register(HeatingType)
class HeatingTypeAdmin(ImportExportModelAdmin):
    resource_class = HeatingTypeResource
    list_display = ("name", "pl")
    search_fields = ("name", "pl")


@admin.register(OwnershipType)
class OwnershipTypeAdmin(ImportExportModelAdmin):
    resource_class = OwnershipTypeResource
    list_display = ("name", "pl")
    search_fields = ("name", "pl")


@admin.register(ApartmentListing)
class ApartmentListingAdmin(ImportExportModelAdmin):
    resource_class = ApartmentListingResource
    list_display = (
        "url",
        "type",
        "area",
        "price",
        "city",
        "province",
        "market_type",
        "transaction_type",
        "last_seen_at",
        "created_at",
    )
    search_fields = (
        "url",
        "city",
        "province",
        "market_type",
        "transaction_type",
        "last_seen_at",
    )


@admin.register(ApartmentListingChange)
class ApartmentListingChangeAdmin(ImportExportModelAdmin):
    resource_class = ApartmentListingChangeResource
    list_display = ("listing", "field_name", "old_value", "new_value")
    search_fields = ("listing__url", "field_name")
