from django.test import TestCase
from django.utils import timezone
from decimal import Decimal

from .models import (
    NameTranslationModel,
    NameCleanModel,
    Location,
    ApartmentListing,
    ApartmentListingChange,
)


class ModelStrTests(TestCase):
    def test_location_str_includes_non_empty_parts(self):
        loc = Location.objects.create(
            city="Warsaw",
            district="Mokotow",
            subdistrict=None,
            municipality="Warszawa",
            county="mazowieckie",
            postal_code="00-001",
            province="Mazowieckie",
            street=None,
            latitude=Decimal("52.229675000000"),
            longitude=Decimal("21.012230000000"),
        )
        self.assertEqual(
            str(loc),
            "Warsaw, Mokotow, Warszawa, mazowieckie, 00-001, Mazowieckie",
        )

    def test_location_str_skips_empty_parts(self):
        loc = Location.objects.create(
            city="Krakow",
            latitude=Decimal("50.061430000000"),
            longitude=Decimal("19.936580000000"),
        )
        self.assertEqual(str(loc), "Krakow")


class ApartmentListingTests(TestCase):
    def _base_location_kwargs(self):
        return dict(
            city="Gdansk",
            district=None,
            subdistrict=None,
            municipality=None,
            county=None,
            postal_code=None,
            province=None,
            street=None,
            latitude=Decimal("54.352025000000"),
            longitude=Decimal("18.646638000000"),
        )

    def test_apartment_listing_str_returns_url(self):
        apt = ApartmentListing.objects.create(
            url="https://example.com/apt/1",
            type="apartment",
            advertiser_type="owner",
            market_type="primary",
            transaction_type="sell",
            last_seen_at=timezone.now(),
            **self._base_location_kwargs(),
        )
        self.assertEqual(str(apt), "https://example.com/apt/1")

    def test_apartment_listing_unique_url(self):
        ApartmentListing.objects.create(
            url="https://example.com/apt/dup",
            type="apartment",
            advertiser_type="owner",
            market_type="primary",
            transaction_type="sell",
            last_seen_at=timezone.now(),
            **self._base_location_kwargs(),
        )
        with self.assertRaises(Exception):
            # unique constraint on URL
            ApartmentListing.objects.create(
                url="https://example.com/apt/dup",
                type="apartment",
                advertiser_type="owner",
                market_type="primary",
                transaction_type="sell",
                last_seen_at=timezone.now(),
                **self._base_location_kwargs(),
            )

    def test_location_unique_together_enforced(self):
        base = self._base_location_kwargs()
        # First create succeeds
        ApartmentListing.objects.create(
            url="https://example.com/apt/ut1",
            type="apartment",
            advertiser_type="owner",
            market_type="primary",
            transaction_type="sell",
            last_seen_at=timezone.now(),
            **base,
        )
        # Second with same location fields but different URL should still be allowed
        # because unique_together is defined on Location model, not ApartmentListing
        # ApartmentListing inherits from Location, but it overrides Meta, so ensure it does not carry unique_together
        ApartmentListing.objects.create(
            url="https://example.com/apt/ut2",
            type="apartment",
            advertiser_type="owner",
            market_type="primary",
            transaction_type="sell",
            last_seen_at=timezone.now(),
            **base,
        )
        self.assertEqual(ApartmentListing.objects.count(), 2)

    def test_numeric_fields_accept_nulls(self):
        # Verify that optional numeric fields can be null
        apt = ApartmentListing.objects.create(
            url="https://example.com/apt/nulls",
            type="apartment",
            area=None,
            price=None,
            price_per_m=None,
            rent=None,
            advertiser_type="owner",
            market_type="primary",
            transaction_type="sell",
            last_seen_at=timezone.now(),
            **self._base_location_kwargs(),
        )
        self.assertIsNone(apt.area)
        self.assertIsNone(apt.price)
        self.assertIsNone(apt.price_per_m)
        self.assertIsNone(apt.rent)


class ApartmentListingChangeTests(TestCase):
    def setUp(self):
        self.listing = ApartmentListing.objects.create(
            url="https://example.com/apt/change",
            type="apartment",
            advertiser_type="owner",
            market_type="primary",
            transaction_type="sell",
            last_seen_at=timezone.now(),
            city="Poznan",
            latitude=Decimal("52.406374000000"),
            longitude=Decimal("16.925168000000"),
        )

    def test_change_str_contains_listing_url_and_field(self):
        change = ApartmentListingChange.objects.create(
            listing=self.listing,
            field_name="price",
            old_value="1000000",
            new_value="990000",
        )
        self.assertIn(self.listing.url, str(change))
        self.assertIn("price", str(change))

    def test_listing_related_name_changes(self):
        ApartmentListingChange.objects.create(
            listing=self.listing,
            field_name="price",
            old_value="1000000",
            new_value="990000",
        )
        ApartmentListingChange.objects.create(
            listing=self.listing,
            field_name="area",
            old_value="50",
            new_value="55",
        )
        self.assertEqual(self.listing.changes.count(), 2)
