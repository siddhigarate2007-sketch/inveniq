"""Idempotent ingestion pipeline for InvenIQ.

Orchestrates:
1. Ingestion of raw travel datasets
2. Schema & data contract validation
3. Demand un-censoring transformation
4. Idempotent writing to Parquet Lakehouse
5. Registration of DuckDB analytical views
"""

from pathlib import Path
from typing import Any
import duckdb
import pandas as pd
import structlog
from inveniq_pipelines.censoring.tobit_correction import DemandCensoringCorrection
from inveniq_pipelines.synthetic.generator import SyntheticDataGenerator
from inveniq_pipelines.validation.schemas import DatasetValidator

logger = structlog.get_logger(__name__)


class LakehouseIngestionLoader:
    """Manages idempotent validation and ingestion into the Parquet Lakehouse."""

    def __init__(
        self,
        raw_data_dir: Path | str | None = None,
        lakehouse_dir: Path | str | None = None,
    ) -> None:
        self.raw_dir = (
            Path(raw_data_dir)
            if raw_data_dir
            else Path(__file__).resolve().parents[4] / "data" / "raw"
        )
        self.lakehouse_dir = (
            Path(lakehouse_dir)
            if lakehouse_dir
            else Path(__file__).resolve().parents[4] / "data" / "lakehouse"
        )
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.lakehouse_dir.mkdir(parents=True, exist_ok=True)
        self.censoring_engine = DemandCensoringCorrection()

    def run_pipeline(self) -> dict[str, Any]:
        """Runs end-to-end ingestion pipeline."""
        logger.info("Initiating InvenIQ ingestion and validation pipeline")

        # 1. Load or Generate Datasets
        calendar_file = self.raw_dir / "dim_calendar.csv"
        if not calendar_file.exists():
            logger.info("Raw data not found. Triggering synthetic generator...")
            gen = SyntheticDataGenerator()
            raw_datasets = gen.generate_all_datasets(self.raw_dir)
        else:
            raw_datasets = {}
            for f in self.raw_dir.glob("*.csv"):
                table_name = f.stem
                raw_datasets[table_name] = pd.read_csv(f)
                # Parse dates
                for date_col in ["calendar_date", "travel_date", "effective_start", "effective_end", "signal_date"]:
                    if date_col in raw_datasets[table_name].columns:
                        raw_datasets[table_name][date_col] = pd.to_datetime(
                            raw_datasets[table_name][date_col]
                        ).dt.date
                for ts_col in ["booking_ts", "cancel_ts", "search_ts"]:
                    if ts_col in raw_datasets[table_name].columns:
                        raw_datasets[table_name][ts_col] = pd.to_datetime(
                            raw_datasets[table_name][ts_col]
                        )

        # 2. Schema Validation Checks
        validation_reports = {}
        for table_name, df in raw_datasets.items():
            if table_name in DatasetValidator.REQUIRED_COLUMNS:
                report = DatasetValidator.validate_table(table_name, df)
                validation_reports[table_name] = report

        # 3. Apply Demand Un-censoring Correction
        logger.info("Applying demand un-censoring to recover latent booking demand")
        fact_demand_uncensored = self.censoring_engine.uncensor_demand(
            df_bookings=raw_datasets["fact_bookings"],
            df_searches=raw_datasets["fact_searches"],
            df_soldouts=raw_datasets["fact_soldouts"],
        )
        raw_datasets["fact_demand_uncensored"] = fact_demand_uncensored

        # 4. Idempotent Parquet Lakehouse Writes
        lakehouse_manifest = {}
        for table_name, df in raw_datasets.items():
            table_path = self.lakehouse_dir / table_name
            table_path.mkdir(parents=True, exist_ok=True)
            parquet_file = table_path / "data.parquet"

            # Write clean columnar Parquet using DuckDB native parquet engine
            escaped_parquet = str(parquet_file).replace("\\", "/")
            con_temp = duckdb.connect()
            con_temp.register("temp_df", df)
            con_temp.execute(f"COPY temp_df TO '{escaped_parquet}' (FORMAT PARQUET)")
            con_temp.close()
            lakehouse_manifest[table_name] = {
                "rows": len(df),
                "columns": list(df.columns),
                "path": str(parquet_file),
            }
            logger.info("Written to Parquet lakehouse", table=table_name, rows=len(df))

        # 5. Initialize DuckDB Catalog Views
        db_path = self.lakehouse_dir / "inveniq_lake.duckdb"
        con = duckdb.connect(str(db_path))
        for table_name, meta in lakehouse_manifest.items():
            escaped_path = meta["path"].replace("\\", "/")
            con.execute(f"CREATE OR REPLACE VIEW {table_name} AS SELECT * FROM read_parquet('{escaped_path}');")
        con.close()
        logger.info("DuckDB lakehouse views created successfully", db_path=str(db_path))

        summary = {
            "status": "SUCCESS",
            "tables_processed": len(lakehouse_manifest),
            "manifest": lakehouse_manifest,
            "duckdb_database": str(db_path),
        }
        return summary


if __name__ == "__main__":
    loader = LakehouseIngestionLoader()
    summary = loader.run_pipeline()
    print("Pipeline Execution Summary:", summary["status"], f"Tables: {summary['tables_processed']}")
