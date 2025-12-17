from django.db import models
from core.models import BaseModel


class NameTranslationModel(BaseModel):
    name = models.CharField(max_length=128, unique=True)
    pl = models.CharField(max_length=128, blank=True, null=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class NameCleanModel(BaseModel):
    name = models.CharField(max_length=128, unique=True)
    clean_name = models.CharField(max_length=128, blank=True, null=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class LocationBase(BaseModel):
    city = models.CharField(max_length=128)
    district = models.CharField(max_length=128, blank=True, null=True)
    subdistrict = models.CharField(max_length=128, blank=True, null=True)
    municipality = models.CharField(max_length=128, blank=True, null=True)
    county = models.CharField(max_length=128, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    province = models.CharField(max_length=128, blank=True, null=True)
    street = models.CharField(max_length=256, blank=True, null=True)
    latitude = models.DecimalField(max_digits=15, decimal_places=12)
    longitude = models.DecimalField(max_digits=15, decimal_places=12)

    class Meta:
        abstract = True


class Location(LocationBase):

    def __str__(self):
        parts = [
            self.city,
            self.district,
            self.subdistrict,
            self.municipality,
            self.county,
            self.postal_code,
            self.province,
            self.street,
        ]
        return ", ".join([p for p in parts if p])

    class Meta:
        db_table = "location"
        unique_together = (
            "latitude",
            "longitude",
        )


class AdvertiserType(NameTranslationModel):
    class Meta(NameTranslationModel.Meta):
        db_table = "advertiser_type"


class AdvertiserName(BaseModel):
    name = models.CharField(max_length=128, unique=True)
    clean_name = models.CharField(max_length=128, blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "advertiser_name"


class DevelopmentName(BaseModel):
    name = models.CharField(max_length=128, unique=True)
    clean_name = models.CharField(max_length=128, blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "development_name"


class MarketType(NameTranslationModel):
    class Meta(NameTranslationModel.Meta):
        db_table = "market_type"


class TransactionType(NameTranslationModel):
    class Meta(NameTranslationModel.Meta):
        db_table = "transaction_type"


class PropertyType(NameTranslationModel):
    class Meta(NameTranslationModel.Meta):
        db_table = "property_type"


class Room(NameTranslationModel):
    class Meta(NameTranslationModel.Meta):
        db_table = "room"


class Floor(NameTranslationModel):
    class Meta(NameTranslationModel.Meta):
        db_table = "floor"


class BuildingFloor(NameTranslationModel):
    class Meta(NameTranslationModel.Meta):
        db_table = "building_floor"


class ConstructionStatus(NameTranslationModel):
    class Meta(NameTranslationModel.Meta):
        db_table = "construction_status"
        verbose_name_plural = "construction_statuses"


class BuildingType(NameTranslationModel):
    class Meta(NameTranslationModel.Meta):
        db_table = "building_type"


class BuildingMaterial(NameTranslationModel):
    class Meta(NameTranslationModel.Meta):
        db_table = "building_material"


class HeatingType(NameTranslationModel):
    class Meta(NameTranslationModel.Meta):
        db_table = "heating_type"


class OwnershipType(NameTranslationModel):
    class Meta(NameTranslationModel.Meta):
        db_table = "ownership_type"


class ApartmentListing(LocationBase):
    url = models.URLField(unique=True)
    type = models.CharField(max_length=128)
    area = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    price_per_m = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    rooms_num = models.CharField(max_length=128, blank=True, null=True)
    floor_no = models.CharField(max_length=128, blank=True, null=True)
    building_floors_num = models.CharField(max_length=128, blank=True, null=True)
    build_year = models.IntegerField(blank=True, null=True)
    construction_status = models.CharField(max_length=128, blank=True, null=True)
    building_type = models.CharField(max_length=128, blank=True, null=True)
    building_material = models.CharField(max_length=128, blank=True, null=True)
    heating_type = models.CharField(max_length=128, blank=True, null=True)
    ownership_type = models.CharField(max_length=128, blank=True, null=True)
    rent = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    advertiser_type = models.CharField(max_length=128)
    advertiser_name = models.CharField(max_length=128, blank=True, null=True)
    development_name = models.CharField(max_length=128, blank=True, null=True)
    market_type = models.CharField(max_length=128)
    transaction_type = models.CharField(max_length=128)
    last_seen_at = models.DateTimeField()

    def __str__(self):
        return self.url

    class Meta:
        db_table = "apartment_listing"


class ApartmentListingChange(BaseModel):
    listing = models.ForeignKey(
        ApartmentListing, on_delete=models.CASCADE, related_name="changes"
    )
    field_name = models.CharField(max_length=128)
    old_value = models.TextField(blank=True, null=True)
    new_value = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.listing.url} - {self.field_name} changed at {self.created_at}"

    class Meta:
        db_table = "apartment_listing_change"
