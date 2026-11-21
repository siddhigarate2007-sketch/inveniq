"""Unit tests for Pydantic domain models in inveniq_core."""

from datetime import date, datetime
import pytest
from pydantic import ValidationError
from inveniq_core.schemas.entities import (
    Destination,
    HotelProperty,
    FlightRoute,
    Supplier,
    CalendarDay,
    BookingRecord,
    SearchRecord,
    SoldOutRecord,
    SupplierTerms,
    ExternalSignals,
)


def test_destination_validation() -> None:
    dest = Destination(
        destination_id="DEST_GOA",
        name="Goa",
        country="India",
        region="West India",
        tier=2,
        domestic_flag=True,
        peak_season_months=[11, 12, 1, 2],
    )
    assert dest.destination_id == "DEST_GOA"
    assert dest.domestic_flag is True

    with pytest.raises(ValidationError):
        Destination(
            destination_id="DEST_BAD",
            name="Bad Tier",
            country="India",
            region="West",
            tier=4,  # tier must be <= 3
            domestic_flag=True,
            peak_season_months=[1],
        )


def test_hotel_property_validation() -> None:
    htl = HotelProperty(
        property_id="HTL_001",
        destination_id="DEST_GOA",
        name="Grand Goa Resort",
        star_rating=5,
        room_category="Deluxe",
        total_rooms=100,
        base_cost_inr=8500.0,
        segment="Luxury",
    )
    assert htl.star_rating == 5
    assert htl.base_cost_inr == 8500.0


def test_booking_record_margin_calculation() -> None:
    bkg = BookingRecord(
        booking_id="BKG_001",
        booking_ts=datetime(2024, 1, 1, 10, 0),
        travel_date=date(2024, 1, 15),
        lead_time_days=14,
        product_type="HOTEL",
        entity_id="HTL_001",
        supplier_id="SUP_001",
        destination_id="DEST_GOA",
        quantity=2,
        sell_price_inr=10000.0,
        cost_price_inr=8000.0,
        margin_inr=2000.0,
        cancelled_flag=False,
    )
    assert bkg.margin_inr == 2000.0
    assert bkg.quantity == 2


def test_supplier_reliability_bounds() -> None:
    supp = Supplier(
        supplier_id="SUP_001",
        name="Global Bedbank",
        supplier_type="Bedbank Wholesaler",
        credit_rating="AA",
        reliability_score=0.95,
        payment_terms_days=30,
    )
    assert supp.reliability_score == 0.95

    with pytest.raises(ValidationError):
        Supplier(
            supplier_id="SUP_BAD",
            name="Bad Supplier",
            supplier_type="Bedbank",
            credit_rating="B",
            reliability_score=1.5,  # must be <= 1.0
            payment_terms_days=30,
        )
