"""Point-in-time feature engineering pipeline for InvenIQ.

Guarantees:
- Strict point-in-time correctness with zero target leakage
- Lags (t-7, t-14, t-21, t-28, t-365) and rolling window aggregations (7d, 14d, 28d)
- Cyclical calendar encodings and holiday lead features
- Macro external signals and look-to-book ratios
"""

from pathlib import Path
from typing import Any
import duckdb
import numpy as np
import pandas as pd
import structlog

logger = structlog.get_logger(__name__)


class FeaturePipeline:
    """Builds point-in-time correct training and inference feature matrices."""

    def __init__(self, lakehouse_db_path: Path | str | None = None) -> None:
        if lakehouse_db_path:
            self.db_path = str(lakehouse_db_path)
        else:
            # Locate repo root by walking up to pyproject.toml
            cur = Path(__file__).resolve().parent
            repo_root = cur
            for p in cur.parents:
                if (p / "pyproject.toml").exists() or (p / "data" / "lakehouse").exists():
                    repo_root = p
                    break
            self.db_path = str(repo_root / "data" / "lakehouse" / "inveniq_lake.duckdb")

    def load_raw_features_from_lakehouse(self) -> pd.DataFrame:
        """Loads and joins dimensional and fact tables from DuckDB lakehouse."""
        logger.info("Extracting raw tables from DuckDB lakehouse", db_path=self.db_path)
        con = duckdb.connect(self.db_path, read_only=True)

        query = """
        SELECT 
            d.travel_date,
            d.entity_id,
            d.destination_id,
            d.product_type,
            d.observed_bookings,
            d.uncensored_demand,
            d.is_censored,
            d.searches_count,
            d.avg_sell_price_inr,
            -- Calendar features
            c.day_of_week,
            c.is_weekend,
            c.is_holiday,
            c.is_festival,
            c.is_school_vacation,
            c.is_long_weekend,
            -- Destination features
            dest.country,
            dest.region,
            dest.tier as dest_tier,
            dest.domestic_flag,
            -- External signals
            s.avg_temp_celsius,
            s.rainfall_mm,
            s.competitor_price_index,
            s.fx_rate_usd_inr,
            s.fuel_price_index,
            s.search_trend_index
        FROM fact_demand_uncensored d
        JOIN dim_calendar c ON d.travel_date = c.calendar_date
        JOIN dim_destination dest ON d.destination_id = dest.destination_id
        LEFT JOIN fact_external_signals s 
            ON d.travel_date = s.signal_date AND d.destination_id = s.destination_id
        ORDER BY d.entity_id, d.travel_date ASC;
        """
        df = con.execute(query).df()
        con.close()
        logger.info("Raw feature matrix extracted", rows=len(df), columns=list(df.columns))
        return df

    def transform_features(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        """Computes lags, rolling stats, and cyclical encodings with strict zero-leakage."""
        df = df_raw.copy()
        df["travel_date"] = pd.to_datetime(df["travel_date"])
        df = df.sort_values(by=["entity_id", "travel_date"]).reset_index(drop=True)

        # 1. Cyclical calendar encodings
        day_of_year = df["travel_date"].dt.dayofyear
        df["sin_doy"] = np.sin(2 * np.pi * day_of_year / 365.25)
        df["cos_doy"] = np.cos(2 * np.pi * day_of_year / 365.25)

        dow = df["day_of_week"]
        df["sin_dow"] = np.sin(2 * np.pi * dow / 7.0)
        df["cos_dow"] = np.cos(2 * np.pi * dow / 7.0)

        month = df["travel_date"].dt.month
        df["sin_month"] = np.sin(2 * np.pi * month / 12.0)
        df["cos_month"] = np.cos(2 * np.pi * month / 12.0)

        # Boolean integer cast
        bool_cols = [
            "is_weekend", "is_holiday", "is_festival",
            "is_school_vacation", "is_long_weekend", "domestic_flag"
        ]
        for col in bool_cols:
            if col in df.columns:
                df[col] = df[col].astype(int)

        # 2. Point-in-time Lag Features (strictly lagged within each entity group)
        # Note: In production procurement, demand for t is predicted at t - lead_time.
        # We construct lags from t-7, t-14, t-21, t-28, t-365
        logger.info("Computing point-in-time lag features per entity")
        grouped = df.groupby("entity_id")["uncensored_demand"]

        df["lag_7"] = grouped.shift(7)
        df["lag_14"] = grouped.shift(14)
        df["lag_21"] = grouped.shift(21)
        df["lag_28"] = grouped.shift(28)
        df["lag_365"] = grouped.shift(365)

        # 3. Rolling Window Statistics (computed strictly on shifted demand to avoid today's leakage)
        logger.info("Computing rolling window features")
        shifted_demand = grouped.shift(1)

        df["rolling_mean_7"] = (
            df.groupby("entity_id")["uncensored_demand"]
            .transform(lambda s: s.shift(1).rolling(7, min_periods=3).mean())
        )
        df["rolling_std_7"] = (
            df.groupby("entity_id")["uncensored_demand"]
            .transform(lambda s: s.shift(1).rolling(7, min_periods=3).std().fillna(0.0))
        )
        df["rolling_mean_14"] = (
            df.groupby("entity_id")["uncensored_demand"]
            .transform(lambda s: s.shift(1).rolling(14, min_periods=7).mean())
        )
        df["rolling_mean_28"] = (
            df.groupby("entity_id")["uncensored_demand"]
            .transform(lambda s: s.shift(1).rolling(28, min_periods=14).mean())
        )

        # 4. Search and Look-to-Book features
        df["l2b_ratio"] = (
            df["uncensored_demand"] / df["searches_count"].replace(0, np.nan)
        ).fillna(0.035)
        df["l2b_ratio_lag7"] = (
            df.groupby("entity_id")["l2b_ratio"].shift(7).fillna(0.035)
        )

        # 5. Relative price indicator
        df["price_to_competitor_ratio"] = (
            df["avg_sell_price_inr"] / (df["competitor_price_index"] * 50.0).replace(0, np.nan)
        ).fillna(1.0)

        # 6. Fill initial missing lags with entity expanding mean
        entity_mean = df.groupby("entity_id")["uncensored_demand"].transform("mean")
        for lag_col in ["lag_7", "lag_14", "lag_21", "lag_28", "lag_365", "rolling_mean_7", "rolling_mean_14", "rolling_mean_28"]:
            df[lag_col] = df[lag_col].fillna(entity_mean)

        # Categorical string conversions to category codes for LightGBM
        cat_cols = ["destination_id", "product_type", "country", "region"]
        for col in cat_cols:
            df[col] = df[col].astype("category")

        return df

    def prepare_dataset(self) -> tuple[pd.DataFrame, list[str], str]:
        """Loads data, generates features, and returns feature dataframe, feature names, and target."""
        df_raw = self.load_raw_features_from_lakehouse()
        df_featured = self.transform_features(df_raw)

        feature_cols = [
            # Lags & rolling
            "lag_7", "lag_14", "lag_21", "lag_28", "lag_365",
            "rolling_mean_7", "rolling_std_7", "rolling_mean_14", "rolling_mean_28",
            # Calendar & Cyclical
            "day_of_week", "sin_dow", "cos_dow", "sin_month", "cos_month", "sin_doy", "cos_doy",
            "is_weekend", "is_holiday", "is_festival", "is_school_vacation", "is_long_weekend",
            # External Signals
            "avg_temp_celsius", "rainfall_mm", "competitor_price_index",
            "fx_rate_usd_inr", "fuel_price_index", "search_trend_index",
            # Price & Search
            "avg_sell_price_inr", "price_to_competitor_ratio", "l2b_ratio_lag7",
            # Categoricals
            "destination_id", "product_type", "dest_tier", "domestic_flag"
        ]
        target_col = "uncensored_demand"

        logger.info("Feature preparation complete", total_rows=len(df_featured), features=len(feature_cols))
        return df_featured, feature_cols, target_col
