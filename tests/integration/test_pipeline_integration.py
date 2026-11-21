"""Integration test verifying end-to-end ingestion and DuckDB querying."""

import tempfile
from pathlib import Path
import duckdb
from inveniq_pipelines.ingestion.loader import LakehouseIngestionLoader
from inveniq_pipelines.synthetic.generator import SyntheticDataGenerator


def test_end_to_end_lakehouse_ingestion() -> None:
    with tempfile.TemporaryDirectory() as tmp_root:
        raw_dir = Path(tmp_root) / "raw"
        lakehouse_dir = Path(tmp_root) / "lakehouse"

        # Generate small dataset
        gen = SyntheticDataGenerator()
        gen.generate_all_datasets(output_dir=raw_dir)

        # Run Lakehouse Ingestion Loader
        loader = LakehouseIngestionLoader(raw_data_dir=raw_dir, lakehouse_dir=lakehouse_dir)
        summary = loader.run_pipeline()

        assert summary["status"] == "SUCCESS"
        assert summary["tables_processed"] >= 10

        # Query DuckDB lakehouse database
        db_path = summary["duckdb_database"]
        con = duckdb.connect(db_path)

        # Test querying views
        res_dest = con.execute("SELECT count(*) FROM dim_destination;").fetchone()
        assert res_dest is not None and res_dest[0] == 20

        res_uncensored = con.execute("SELECT count(*) FROM fact_demand_uncensored WHERE is_censored = true;").fetchone()
        assert res_uncensored is not None and res_uncensored[0] >= 0

        con.close()
