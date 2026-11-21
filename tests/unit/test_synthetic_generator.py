"""Unit tests for synthetic data generator."""

import tempfile
from pathlib import Path
import pytest
from inveniq_pipelines.synthetic.generator import SyntheticDataGenerator


def test_generator_deterministic_output() -> None:
    gen1 = SyntheticDataGenerator()
    gen2 = SyntheticDataGenerator()

    cal1 = gen1.generate_calendar()
    cal2 = gen2.generate_calendar()

    assert len(cal1) == len(cal2)
    assert (cal1["calendar_date"] == cal2["calendar_date"]).all()
    assert (cal1["is_festival"] == cal2["is_festival"]).all()


def test_generator_destinations_and_suppliers() -> None:
    gen = SyntheticDataGenerator()
    dest = gen.generate_destinations()
    supp = gen.generate_suppliers(count=20)

    assert len(dest) == 20
    assert len(supp) == 20
    assert "DEST_GOA" in dest["destination_id"].values
    assert "DEST_DUBAI" in dest["destination_id"].values
    assert (supp["reliability_score"] >= 0.80).all()


def test_generator_full_pipeline_output() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        gen = SyntheticDataGenerator()
        datasets = gen.generate_all_datasets(output_dir=tmp_dir)

        expected_tables = [
            "dim_calendar",
            "dim_destination",
            "dim_supplier",
            "dim_property",
            "dim_route",
            "fact_supplier_terms",
            "fact_external_signals",
            "fact_searches",
            "fact_bookings",
            "fact_soldouts",
        ]
        for tbl in expected_tables:
            assert tbl in datasets
            assert len(datasets[tbl]) > 0
            assert (Path(tmp_dir) / f"{tbl}.csv").exists()

        assert (Path(tmp_dir) / "ground_truth_parameters.json").exists()
