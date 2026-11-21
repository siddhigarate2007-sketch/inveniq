"""Data validation schemas and contract enforcement for InvenIQ."""

from typing import Any
import pandas as pd
import structlog

logger = structlog.get_logger(__name__)


class DataValidationError(Exception):
    """Raised when an ingested dataframe violates quality contracts."""
    pass


class DatasetValidator:
    """Validates ingested raw dataframes against schema contracts."""

    REQUIRED_COLUMNS: dict[str, list[str]] = {
        "dim_destination": [
            "destination_id", "name", "country", "region", "tier", "domestic_flag"
        ],
        "dim_property": [
            "property_id", "destination_id", "name", "star_rating", "room_category",
            "total_rooms", "base_cost_inr", "segment"
        ],
        "dim_route": [
            "route_id", "origin_airport", "destination_airport", "destination_id",
            "airline", "flight_number", "cabin_class", "daily_capacity", "base_cost_inr"
        ],
        "dim_supplier": [
            "supplier_id", "name", "supplier_type", "credit_rating", "reliability_score",
            "payment_terms_days"
        ],
        "dim_calendar": [
            "calendar_date", "day_of_week", "is_weekend", "is_holiday", "is_festival",
            "is_school_vacation", "is_long_weekend"
        ],
        "fact_bookings": [
            "booking_id", "booking_ts", "travel_date", "lead_time_days", "product_type",
            "entity_id", "supplier_id", "destination_id", "quantity", "sell_price_inr",
            "cost_price_inr", "margin_inr", "cancelled_flag"
        ],
        "fact_searches": [
            "search_id", "search_ts", "product_type", "destination_id", "entity_id",
            "travel_date", "results_shown", "clicks", "bookings_count"
        ],
        "fact_soldouts": [
            "soldout_id", "entity_id", "destination_id", "travel_date", "allotment_capacity",
            "duration_hours", "unmet_searches", "estimated_lost_demand"
        ],
        "fact_supplier_terms": [
            "term_id", "supplier_id", "entity_id", "effective_start", "effective_end",
            "unit_cost_inr", "allotment_size", "min_order_qty", "release_cutoff_days",
            "cancellation_penalty_pct"
        ],
        "fact_external_signals": [
            "signal_id", "signal_date", "destination_id", "avg_temp_celsius", "rainfall_mm",
            "competitor_price_index", "fx_rate_usd_inr", "fuel_price_index", "search_trend_index"
        ],
    }

    @classmethod
    def validate_table(cls, table_name: str, df: pd.DataFrame) -> dict[str, Any]:
        """Runs contract checks on dataframe. Raises DataValidationError on failure."""
        if table_name not in cls.REQUIRED_COLUMNS:
            raise DataValidationError(f"Unknown table: {table_name}")

        report: dict[str, Any] = {
            "table_name": table_name,
            "row_count": len(df),
            "passed": True,
            "errors": [],
            "warnings": [],
        }

        if df.empty:
            msg = f"Table {table_name} is empty (0 rows)."
            report["errors"].append(msg)
            report["passed"] = False
            raise DataValidationError(msg)

        # 1. Column presence check
        expected_cols = cls.REQUIRED_COLUMNS[table_name]
        missing = [col for col in expected_cols if col not in df.columns]
        if missing:
            msg = f"Table {table_name} missing required columns: {missing}"
            report["errors"].append(msg)
            report["passed"] = False
            raise DataValidationError(msg)

        # 2. Key null checks
        null_counts = df[expected_cols].isnull().sum()
        critical_cols = [
            c for c in expected_cols
            if not c.endswith(("_name", "notes", "cancel_ts", "entity_id"))
        ]
        for col in critical_cols:
            if col in null_counts and null_counts[col] > 0:
                msg = f"Table {table_name} column '{col}' has {null_counts[col]} null values."
                report["errors"].append(msg)
                report["passed"] = False

        # 3. Numeric range checks
        if table_name == "fact_bookings":
            if (df["quantity"] <= 0).any():
                report["errors"].append("fact_bookings contains non-positive quantity.")
                report["passed"] = False
            if (df["sell_price_inr"] <= 0).any() or (df["cost_price_inr"] <= 0).any():
                report["errors"].append("fact_bookings contains non-positive prices.")
                report["passed"] = False
            if (df["lead_time_days"] < 0).any():
                report["errors"].append("fact_bookings contains negative lead_time_days.")
                report["passed"] = False

        if table_name == "dim_supplier":
            if not ((df["reliability_score"] >= 0.0) & (df["reliability_score"] <= 1.0)).all():
                report["errors"].append("dim_supplier reliability_score outside [0, 1].")
                report["passed"] = False

        if table_name == "fact_external_signals":
            if (df["competitor_price_index"] < 20).any() or (df["competitor_price_index"] > 300).any():
                report["errors"].append("competitor_price_index out of realistic range [20, 300].")
                report["passed"] = False

        if not report["passed"]:
            logger.error("Data contract validation failed", report=report)
            raise DataValidationError(f"Validation failed for {table_name}: {report['errors']}")

        logger.info("Data contract validation passed", table=table_name, rows=len(df))
        return report
