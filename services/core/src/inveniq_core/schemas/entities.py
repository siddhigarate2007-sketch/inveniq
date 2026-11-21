from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class Destination(BaseModel):
    """Geographic travel destination entity."""

    destination_id: str = Field(..., description="Unique destination identifier, e.g. DEST_GOA")
    name: str = Field(..., description="City / Region name")
    country: str = Field(..., description="Country name")
    region: str = Field(..., description="Sub-region, e.g. South Asia, Middle East")
    tier: int = Field(..., ge=1, le=3, description="Market tier: 1=Tier-1 Metro, 2=Holiday Hotspot, 3=Emerging")
    domestic_flag: bool = Field(..., description="True if domestic India destination")
    peak_season_months: list[int] = Field(
        ..., description="List of peak month integers (1-12)"
    )


class HotelProperty(BaseModel):
    """Hotel accommodation entity."""

    property_id: str = Field(..., description="Unique hotel identifier, e.g. HTL_GOA_001")
    destination_id: str = Field(..., description="Foreign key to Destination")
    name: str = Field(..., description="Hotel property name")
    star_rating: int = Field(..., ge=2, le=5, description="Star classification (2-5)")
    room_category: str = Field(..., description="Standard, Deluxe, Executive Suite")
    total_rooms: int = Field(..., gt=0, description="Property room capacity")
    base_cost_inr: float = Field(..., gt=0, description="Contracted standard room-night cost in INR")
    segment: str = Field(..., description="Budget, Midscale, Luxury")


class FlightRoute(BaseModel):
    """Flight transportation route entity."""

    route_id: str = Field(..., description="Unique route identifier, e.g. FLT_BOM_GOI_01")
    origin_airport: str = Field(..., description="Origin 3-letter IATA code, e.g. DEL, BOM")
    destination_airport: str = Field(..., description="Destination IATA code")
    destination_id: str = Field(..., description="Foreign key to Destination")
    airline: str = Field(..., description="Operating airline carrier name")
    flight_number: str = Field(..., description="Flight code, e.g. 6E-204")
    cabin_class: str = Field(..., description="Economy, Premium Economy, Business")
    daily_capacity: int = Field(..., gt=0, description="Seats allocated to wholesale distribution")
    base_cost_inr: float = Field(..., gt=0, description="Contracted standard seat cost in INR")


class Supplier(BaseModel):
    """Certified wholesale travel inventory supplier."""

    supplier_id: str = Field(..., description="Unique supplier identifier, e.g. SUP_001")
    name: str = Field(..., description="Supplier / Bedbank name")
    supplier_type: str = Field(..., description="Direct Hotel Chain, Bedbank, Airline Consolidator")
    credit_rating: str = Field(..., description="AAA, AA, A, BBB")
    reliability_score: float = Field(..., ge=0.0, le=1.0, description="Fulfillment reliability index")
    payment_terms_days: int = Field(..., ge=0, description="Credit window in days (e.g. 30)")


class CalendarDay(BaseModel):
    """Calendar dimension record."""

    calendar_date: date = Field(..., description="Calendar date YYYY-MM-DD")
    day_of_week: int = Field(..., ge=0, le=6, description="0=Monday, 6=Sunday")
    is_weekend: bool = Field(..., description="True if Saturday or Sunday")
    is_holiday: bool = Field(default=False, description="True if public holiday")
    holiday_name: Optional[str] = Field(default=None, description="Name of public holiday")
    is_festival: bool = Field(default=False, description="True if major festival")
    festival_name: Optional[str] = Field(default=None, description="Diwali, Eid, Christmas, etc.")
    is_school_vacation: bool = Field(default=False, description="True during summer/winter school breaks")
    is_long_weekend: bool = Field(default=False, description="True if holiday adjacent to weekend")


class BookingRecord(BaseModel):
    """Historical transaction booking fact record."""

    booking_id: str = Field(..., description="Unique booking ID")
    booking_ts: datetime = Field(..., description="Booking creation timestamp")
    travel_date: date = Field(..., description="Target check-in / departure date")
    lead_time_days: int = Field(..., ge=0, description="Days between booking and travel date")
    product_type: str = Field(..., description="'HOTEL' or 'FLIGHT'")
    entity_id: str = Field(..., description="property_id or route_id")
    supplier_id: str = Field(..., description="Supplier ID providing inventory")
    destination_id: str = Field(..., description="Destination identifier")
    quantity: int = Field(..., gt=0, description="Number of rooms or seats booked")
    sell_price_inr: float = Field(..., gt=0, description="Price charged to travel agent")
    cost_price_inr: float = Field(..., gt=0, description="Price paid to supplier")
    margin_inr: float = Field(..., description="sell_price - cost_price")
    cancelled_flag: bool = Field(default=False, description="True if booking was cancelled")
    cancel_ts: Optional[datetime] = Field(default=None, description="Cancellation timestamp")

    @field_validator("margin_inr", mode="before")
    @classmethod
    def calculate_margin(cls, v: Optional[float], info) -> float:
        if v is not None:
            return v
        data = info.data
        sell = data.get("sell_price_inr", 0.0)
        cost = data.get("cost_price_inr", 0.0)
        return float(sell - cost)


class SearchRecord(BaseModel):
    """Platform search query fact record."""

    search_id: str = Field(..., description="Unique search query ID")
    search_ts: datetime = Field(..., description="Search execution timestamp")
    product_type: str = Field(..., description="'HOTEL' or 'FLIGHT'")
    destination_id: str = Field(..., description="Target destination ID")
    entity_id: Optional[str] = Field(default=None, description="Specific hotel or route searched")
    travel_date: date = Field(..., description="Intended travel date")
    results_shown: int = Field(..., ge=0, description="Number of results returned")
    clicks: int = Field(..., ge=0, description="Number of inventory clicks")
    bookings_count: int = Field(default=0, ge=0, description="Resulting conversions")


class SoldOutRecord(BaseModel):
    """Sold-out capacity fact record for demand censoring adjustment."""

    soldout_id: str = Field(..., description="Unique sold-out event ID")
    entity_id: str = Field(..., description="property_id or route_id")
    destination_id: str = Field(..., description="Destination ID")
    travel_date: date = Field(..., description="Date on which allotment was fully exhausted")
    allotment_capacity: int = Field(..., gt=0, description="Total allotment available")
    duration_hours: float = Field(..., ge=0.0, description="Hours inventory remained sold out")
    unmet_searches: int = Field(..., ge=0, description="Searches received while sold out")
    estimated_lost_demand: float = Field(..., ge=0.0, description="Uplift latent demand estimate")


class SupplierTerms(BaseModel):
    """Contract terms and commitments per supplier and inventory entity."""

    term_id: str = Field(..., description="Contract term ID")
    supplier_id: str = Field(..., description="Supplier ID")
    entity_id: str = Field(..., description="property_id or route_id")
    effective_start: date = Field(..., description="Term effective start date")
    effective_end: date = Field(..., description="Term effective end date")
    unit_cost_inr: float = Field(..., gt=0, description="Negotiated wholesale cost per unit")
    allotment_size: int = Field(..., gt=0, description="Maximum available units for pre-buy")
    min_order_qty: int = Field(default=1, ge=1, description="Minimum order quantity (MOQ)")
    release_cutoff_days: int = Field(..., ge=0, description="Cutoff days before travel date")
    cancellation_penalty_pct: float = Field(
        ..., ge=0.0, le=1.0, description="Penalty percentage past cutoff"
    )
    volume_discount_pct: float = Field(
        default=0.0, ge=0.0, le=0.50, description="Discount for buying > 80% allotment"
    )


class ExternalSignals(BaseModel):
    """Macro and environmental external signals."""

    signal_id: str = Field(..., description="Unique signal record ID")
    signal_date: date = Field(..., description="Signal date YYYY-MM-DD")
    destination_id: str = Field(..., description="Destination ID")
    avg_temp_celsius: float = Field(..., description="Average daily temperature in Celsius")
    rainfall_mm: float = Field(..., ge=0.0, description="Precipitation in mm")
    competitor_price_index: float = Field(
        ..., ge=50.0, le=200.0, description="Competitor rate index (100 = parity)"
    )
    fx_rate_usd_inr: float = Field(..., gt=50.0, description="Exchange rate USD to INR")
    fuel_price_index: float = Field(..., gt=0.0, description="Aviation turbine fuel index")
    search_trend_index: float = Field(..., ge=0.0, le=100.0, description="Google/Macro trend index")
