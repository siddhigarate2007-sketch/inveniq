"""Configurable, deterministic synthetic data generator for InvenIQ.

Generates realistic B2B travel marketplace data reflecting:
- Multi-year daily timeline across 20 domestic & international destinations
- Hotels and flights across 50 suppliers
- Seasonality, festival spikes, day-of-week patterns, lead-time curves
- Price elasticity by segment
- Supplier-specific cancellation baselines
- Demand censoring during capacity sold-outs
- Ground-truth parameters exported for ML recovery validation
"""

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd
import structlog
import yaml

logger = structlog.get_logger(__name__)


class SyntheticDataGenerator:
    """Generates synthetic travel marketplace datasets with embedded ground-truth effects."""

    def __init__(self, config_path: Path | str | None = None) -> None:
        if config_path and Path(config_path).exists():
            with open(config_path, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f)
        else:
            default_cfg = Path(__file__).parent / "configs" / "default_sim.yaml"
            if default_cfg.exists():
                with open(default_cfg, "r", encoding="utf-8") as f:
                    self.config = yaml.safe_load(f)
            else:
                self.config = {
                    "simulation": {"seed": 42, "start_date": "2023-01-01", "end_date": "2025-12-31"},
                    "destinations": {"domestic": [], "international": []},
                }

        self.seed = self.config.get("simulation", {}).get("seed", 42)
        np.random.seed(self.seed)
        self.rng = np.random.default_rng(self.seed)

        self.start_date = datetime.strptime(
            self.config.get("simulation", {}).get("start_date", "2023-01-01"), "%Y-%m-%d"
        ).date()
        self.end_date = datetime.strptime(
            self.config.get("simulation", {}).get("end_date", "2025-12-31"), "%Y-%m-%d"
        ).date()
        self.num_days = (self.end_date - self.start_date).days + 1

    def generate_calendar(self) -> pd.DataFrame:
        """Generates dim_calendar with holidays, festivals, and long weekends."""
        records = []
        cur = self.start_date
        while cur <= self.end_date:
            dow = cur.weekday()
            is_wknd = dow in (5, 6)
            month, day = cur.month, cur.day

            is_hol = False
            hol_name = None
            is_fest = False
            fest_name = None

            # Major Indian Holidays & Global Festivals
            if (month == 1 and day == 26) or (month == 8 and day == 15) or (month == 10 and day == 2):
                is_hol = True
                hol_name = "National Holiday"
            elif (month == 12 and day in (24, 25, 31)) or (month == 1 and day == 1):
                is_fest = True
                fest_name = "Christmas / New Year"
            elif (month == 11 and day in (10, 11, 12, 13)) or (month == 10 and day in (22, 23, 24)):
                is_fest = True
                fest_name = "Diwali / Dussehra Peak"
            elif month in (3, 4) and day in (10, 11):
                is_fest = True
                fest_name = "Eid al-Fitr"
            elif month == 3 and day in (24, 25):
                is_fest = True
                fest_name = "Holi"

            is_vacation = month in (5, 6) or (month == 12 and day >= 20)
            is_long_wknd = is_wknd or (is_hol and dow in (0, 4)) or (is_fest and dow in (0, 4))

            records.append({
                "calendar_date": cur,
                "day_of_week": dow,
                "is_weekend": is_wknd,
                "is_holiday": is_hol,
                "holiday_name": hol_name,
                "is_festival": is_fest,
                "festival_name": fest_name,
                "is_school_vacation": is_vacation,
                "is_long_weekend": is_long_wknd,
            })
            cur += timedelta(days=1)

        return pd.DataFrame(records)

    def generate_destinations(self) -> pd.DataFrame:
        """Generates dim_destination."""
        dom = self.config.get("destinations", {}).get("domestic", [])
        intl = self.config.get("destinations", {}).get("international", [])
        rows = []
        for d in dom:
            rows.append({
                "destination_id": d["id"],
                "name": d["name"],
                "country": "India",
                "region": d["region"],
                "tier": d["tier"],
                "domestic_flag": True,
                "base_demand": d.get("base_demand", 100),
                "peak_months": d.get("peak_months", [11, 12, 1]),
            })
        for d in intl:
            rows.append({
                "destination_id": d["id"],
                "name": d["name"],
                "country": d.get("country", "International"),
                "region": d["region"],
                "tier": d["tier"],
                "domestic_flag": False,
                "base_demand": d.get("base_demand", 120),
                "peak_months": d.get("peak_months", [11, 12, 1]),
            })
        return pd.DataFrame(rows)

    def generate_suppliers(self, count: int = 50) -> pd.DataFrame:
        """Generates dim_supplier."""
        types = ["Direct Hotel Chain", "Bedbank Wholesaler", "Airline Consolidator"]
        ratings = ["AAA", "AA", "A", "BBB"]
        rows = []
        for i in range(1, count + 1):
            stype = self.rng.choice(types, p=[0.45, 0.35, 0.20])
            rating = self.rng.choice(ratings, p=[0.25, 0.40, 0.25, 0.10])
            rel = round(float(self.rng.uniform(0.85, 0.99)), 3)
            terms = int(self.rng.choice([15, 30, 45, 60]))
            rows.append({
                "supplier_id": f"SUP_{i:03d}",
                "name": f"Supplier Partner {i:03d} ({stype.split()[0]})",
                "supplier_type": stype,
                "credit_rating": rating,
                "reliability_score": rel,
                "payment_terms_days": terms,
            })
        return pd.DataFrame(rows)

    def generate_properties(self, dim_dest: pd.DataFrame) -> pd.DataFrame:
        """Generates dim_property (hotels)."""
        rows = []
        categories = ["Standard", "Deluxe", "Executive Suite"]
        segments = ["Budget", "Midscale", "Luxury"]
        counter = 1
        for _, dest in dim_dest.iterrows():
            dest_id = dest["destination_id"]
            num_hotels = 3 if dest["tier"] == 1 else 2
            for h in range(num_hotels):
                star = int(self.rng.choice([3, 4, 5], p=[0.3, 0.4, 0.3]))
                seg = "Luxury" if star == 5 else ("Midscale" if star == 4 else "Budget")
                cat = self.rng.choice(categories)
                rooms = int(self.rng.choice([50, 80, 120, 200]))
                base_cost = 2500.0 if seg == "Budget" else (5500.0 if seg == "Midscale" else 12500.0)
                if not dest["domestic_flag"]:
                    base_cost *= 1.6

                rows.append({
                    "property_id": f"HTL_{counter:04d}",
                    "destination_id": dest_id,
                    "name": f"{dest['name']} {seg} Grand {h+1}",
                    "star_rating": star,
                    "room_category": cat,
                    "total_rooms": rooms,
                    "base_cost_inr": round(float(base_cost), 2),
                    "segment": seg,
                })
                counter += 1
        return pd.DataFrame(rows)

    def generate_routes(self, dim_dest: pd.DataFrame) -> pd.DataFrame:
        """Generates dim_route (flights)."""
        rows = []
        origins = ["DEL", "BOM", "BLR"]
        airlines = ["IndiGo", "Air India", "Emirates", "Singapore Airlines", "Thai Airways"]
        counter = 1
        for _, dest in dim_dest.iterrows():
            dest_id = dest["destination_id"]
            iata = dest_id.replace("DEST_", "")[:3]
            origin = self.rng.choice(origins)
            airline = self.rng.choice(airlines)
            cost = 4500.0 if dest["domestic_flag"] else 18000.0
            rows.append({
                "route_id": f"FLT_{counter:04d}",
                "origin_airport": origin,
                "destination_airport": iata,
                "destination_id": dest_id,
                "airline": airline,
                "flight_number": f"{airline[:2].upper()}-{100 + counter}",
                "cabin_class": "Economy",
                "daily_capacity": int(self.rng.choice([30, 50, 80])),
                "base_cost_inr": round(float(cost), 2),
            })
            counter += 1
        return pd.DataFrame(rows)

    def generate_supplier_terms(
        self, dim_prop: pd.DataFrame, dim_route: pd.DataFrame, dim_supp: pd.DataFrame
    ) -> pd.DataFrame:
        """Generates fact_supplier_terms."""
        rows = []
        term_id = 1
        all_entities = [
            (p["property_id"], p["base_cost_inr"], "HOTEL") for _, p in dim_prop.iterrows()
        ] + [
            (r["route_id"], r["base_cost_inr"], "FLIGHT") for _, r in dim_route.iterrows()
        ]

        hotel_supps = dim_supp[dim_supp["supplier_type"] != "Airline Consolidator"]["supplier_id"].tolist()
        flight_supps = dim_supp[dim_supp["supplier_type"] == "Airline Consolidator"]["supplier_id"].tolist()

        for ent_id, cost, ptype in all_entities:
            supp_pool = flight_supps if ptype == "FLIGHT" else hotel_supps
            assigned_supps = self.rng.choice(supp_pool, size=min(2, len(supp_pool)), replace=False)
            for supp_id in assigned_supps:
                allotment = int(self.rng.choice([20, 40, 60, 100]))
                moq = int(self.rng.choice([1, 2, 5]))
                cutoff = int(self.rng.choice([7, 14, 21, 30]))
                penalty = float(self.rng.choice([0.5, 0.75, 1.0]))
                rows.append({
                    "term_id": f"TRM_{term_id:05d}",
                    "supplier_id": supp_id,
                    "entity_id": ent_id,
                    "effective_start": self.start_date,
                    "effective_end": self.end_date,
                    "unit_cost_inr": round(cost * float(self.rng.uniform(0.92, 1.05)), 2),
                    "allotment_size": allotment,
                    "min_order_qty": moq,
                    "release_cutoff_days": cutoff,
                    "cancellation_penalty_pct": penalty,
                    "volume_discount_pct": 0.05 if allotment >= 50 else 0.0,
                })
                term_id += 1
        return pd.DataFrame(rows)

    def generate_external_signals(
        self, dim_calendar: pd.DataFrame, dim_dest: pd.DataFrame
    ) -> pd.DataFrame:
        """Generates fact_external_signals using vectorized numpy operations."""
        dates = dim_calendar["calendar_date"].tolist()
        n_dates = len(dates)
        days_from_start = np.arange(n_dates)
        months = np.array([d.month for d in dates])

        dfs = []
        sig_id_start = 1

        for _, dest in dim_dest.iterrows():
            dest_id = dest["destination_id"]
            is_dom = dest["domestic_flag"]
            base_temp = 28.0 if is_dom else 22.0
            peak_months = set(dest["peak_months"])

            # Vectorized signal calculations
            temp = np.round(base_temp + 6.0 * np.sin((months - 5) / 12.0 * 2 * np.pi) + self.rng.normal(0, 1.5, n_dates), 1)
            rain_scale = np.where(np.isin(months, [6, 7, 8]), 2.0, 0.3)
            rain = np.round(np.maximum(0.0, self.rng.exponential(rain_scale, n_dates)), 1)
            comp_idx = np.round(self.rng.normal(100.0, 8.0, n_dates), 2)
            fx = np.round(83.0 + 0.005 * days_from_start + self.rng.normal(0, 0.5, n_dates), 2)
            fuel_idx = np.round(105.0 + 5.0 * np.sin(months / 12.0 * 2 * np.pi) + self.rng.normal(0, 2.0, n_dates), 2)
            is_peak = np.isin(months, list(peak_months))
            search_idx = np.round(np.clip(50.0 + np.where(is_peak, 30.0, 0.0) + self.rng.normal(0, 5.0, n_dates), 10.0, 100.0), 1)

            sig_ids = [f"SIG_{i:07d}" for i in range(sig_id_start, sig_id_start + n_dates)]
            sig_id_start += n_dates

            df_sub = pd.DataFrame({
                "signal_id": sig_ids,
                "signal_date": dates,
                "destination_id": dest_id,
                "avg_temp_celsius": temp,
                "rainfall_mm": rain,
                "competitor_price_index": comp_idx,
                "fx_rate_usd_inr": fx,
                "fuel_price_index": fuel_idx,
                "search_trend_index": search_idx,
            })
            dfs.append(df_sub)

        return pd.concat(dfs, ignore_index=True)

    def generate_market_transactions(
        self,
        dim_calendar: pd.DataFrame,
        dim_dest: pd.DataFrame,
        dim_prop: pd.DataFrame,
        dim_route: pd.DataFrame,
        supplier_terms: pd.DataFrame,
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Generates fact_searches, fact_bookings, and fact_soldouts via high-speed array operations."""
        dates = dim_calendar["calendar_date"].tolist()
        n_dates = len(dates)
        months = np.array([d.month for d in dates])
        is_wknd = dim_calendar["is_weekend"].to_numpy()
        is_fest = dim_calendar["is_festival"].to_numpy()
        is_long_wknd = dim_calendar["is_long_weekend"].to_numpy()
        fest_names = dim_calendar["festival_name"].fillna("").to_numpy()

        # Precompute calendar multipliers
        fest_mult = np.ones(n_dates)
        for idx in range(n_dates):
            if is_fest[idx]:
                fest_mult[idx] += 1.0 if "Christmas" in str(fest_names[idx]) else 0.7
            if is_long_wknd[idx]:
                fest_mult[idx] += 0.35

        wknd_mult = np.where(is_wknd, 1.3, 0.95)

        terms_map = {}
        for _, term in supplier_terms.iterrows():
            terms_map[term["entity_id"]] = term

        dest_map = {row["destination_id"]: row for _, row in dim_dest.iterrows()}
        elasticity_coeffs = self.config.get("ground_truth_effects", {}).get("elasticity", {
            "Luxury": -0.85, "Midscale": -1.45, "Budget": -2.15
        })

        entities = []
        for _, p in dim_prop.iterrows():
            entities.append({
                "entity_id": p["property_id"],
                "destination_id": p["destination_id"],
                "product_type": "HOTEL",
                "segment": p["segment"],
                "base_cost": p["base_cost_inr"],
            })
        for _, r in dim_route.iterrows():
            entities.append({
                "entity_id": r["route_id"],
                "destination_id": r["destination_id"],
                "product_type": "FLIGHT",
                "segment": "Midscale",
                "base_cost": r["base_cost_inr"],
            })

        booking_list = []
        search_list = []
        soldout_list = []

        booking_counter = 1
        search_counter = 1
        soldout_counter = 1

        for ent in entities:
            ent_id = ent["entity_id"]
            dest_id = ent["destination_id"]
            ptype = ent["product_type"]
            seg = ent["segment"]
            base_cost = ent["base_cost"]
            beta_price = elasticity_coeffs.get(seg, -1.40)

            term = terms_map.get(ent_id)
            allotment = int(term["allotment_size"]) if term is not None else 30
            supp_id = term["supplier_id"] if term is not None else "SUP_001"

            dest_info = dest_map[dest_id]
            base_d = dest_info["base_demand"] / (len(entities) / len(dest_map))
            peak_set = set(dest_info["peak_months"])

            # Seasonality array
            seas_mult = np.where(np.isin(months, list(peak_set)), 1.6, 0.8)

            # Markup and price elasticity
            markup = 1.25 + np.where(seas_mult > 1.0, 0.15, -0.05)
            sell_price = np.round(base_cost * markup, 2)
            price_ratio = sell_price / (base_cost * 1.20)
            elasticity_factor = np.maximum(0.4, price_ratio ** beta_price)

            # Latent mean demand
            mean_demand = np.maximum(1.0, base_d * seas_mult * fest_mult * wknd_mult * elasticity_factor)
            true_latent = self.rng.poisson(mean_demand)

            # Baseline look-to-book
            baseline_l2b = 0.035 * np.where(is_fest, 1.2, 1.0)
            searches = np.maximum((true_latent / baseline_l2b).astype(int), 10) + np.maximum(0, self.rng.normal(20, 5, n_dates).astype(int))
            clicks = (searches * 0.25).astype(int)

            observed_bkg = np.minimum(true_latent, allotment)
            is_soldout = true_latent >= allotment

            # Search DataFrame chunk
            search_ids = [f"SRC_{i:08d}" for i in range(search_counter, search_counter + n_dates)]
            search_counter += n_dates
            search_ts = [datetime.combine(d - timedelta(days=14), datetime.min.time()) for d in dates]

            df_src_chunk = pd.DataFrame({
                "search_id": search_ids,
                "search_ts": search_ts,
                "product_type": ptype,
                "destination_id": dest_id,
                "entity_id": ent_id,
                "travel_date": dates,
                "results_shown": searches,
                "clicks": clicks,
                "bookings_count": observed_bkg,
            })
            search_list.append(df_src_chunk)

            # Sold-out chunk
            soldout_indices = np.where(is_soldout)[0]
            if len(soldout_indices) > 0:
                lost_d = (true_latent[soldout_indices] - allotment).astype(float)
                s_dates = [dates[idx] for idx in soldout_indices]
                s_searches = searches[soldout_indices]
                s_unmet = (lost_d / baseline_l2b[soldout_indices]).astype(int)
                durations = np.round(self.rng.uniform(6.0, 24.0, len(soldout_indices)), 1)
                s_ids = [f"SLD_{i:06d}" for i in range(soldout_counter, soldout_counter + len(soldout_indices))]
                soldout_counter += len(soldout_indices)

                df_sld_chunk = pd.DataFrame({
                    "soldout_id": s_ids,
                    "entity_id": ent_id,
                    "destination_id": dest_id,
                    "travel_date": s_dates,
                    "allotment_capacity": allotment,
                    "duration_hours": durations,
                    "unmet_searches": s_unmet,
                    "estimated_lost_demand": lost_d,
                })
                soldout_list.append(df_sld_chunk)

            # Bookings chunk (only non-zero observed bookings)
            bkg_indices = np.where(observed_bkg > 0)[0]
            if len(bkg_indices) > 0:
                b_dates = [dates[idx] for idx in bkg_indices]
                b_qty = observed_bkg[bkg_indices]
                b_sell = sell_price[bkg_indices]
                b_lead = np.clip(self.rng.exponential(14.0, len(bkg_indices)).astype(int), 1, 90)
                b_ts = [datetime.combine(b_dates[i] - timedelta(days=int(b_lead[i])), datetime.min.time()) for i in range(len(bkg_indices))]

                cancel_p = np.where(b_lead > 20, 0.12, 0.05)
                is_canc = self.rng.uniform(0, 1, len(bkg_indices)) < cancel_p
                canc_ts = [
                    (b_ts[i] + timedelta(days=int(b_lead[i] * 0.5))) if is_canc[i] else None
                    for i in range(len(bkg_indices))
                ]

                b_ids = [f"BKG_{i:08d}" for i in range(booking_counter, booking_counter + len(bkg_indices))]
                booking_counter += len(bkg_indices)

                df_bkg_chunk = pd.DataFrame({
                    "booking_id": b_ids,
                    "booking_ts": b_ts,
                    "travel_date": b_dates,
                    "lead_time_days": b_lead,
                    "product_type": ptype,
                    "entity_id": ent_id,
                    "supplier_id": supp_id,
                    "destination_id": dest_id,
                    "quantity": b_qty,
                    "sell_price_inr": b_sell,
                    "cost_price_inr": base_cost,
                    "margin_inr": np.round(b_sell - base_cost, 2),
                    "cancelled_flag": is_canc,
                    "cancel_ts": canc_ts,
                })
                booking_list.append(df_bkg_chunk)

        df_bkg = pd.concat(booking_list, ignore_index=True) if booking_list else pd.DataFrame()
        df_src = pd.concat(search_list, ignore_index=True) if search_list else pd.DataFrame()
        df_sld = pd.concat(soldout_list, ignore_index=True) if soldout_list else pd.DataFrame()

        return df_bkg, df_src, df_sld

    def generate_all_datasets(self, output_dir: Path | str | None = None) -> dict[str, pd.DataFrame]:
        """Generates all 10 datasets and writes them to disk."""
        out_path = Path(output_dir) if output_dir else Path(__file__).resolve().parents[4] / "data" / "raw"
        out_path.mkdir(parents=True, exist_ok=True)

        logger.info("Starting deterministic synthetic data generation", seed=self.seed)

        dim_calendar = self.generate_calendar()
        dim_destination = self.generate_destinations()
        dim_supplier = self.generate_suppliers(count=self.config.get("suppliers", {}).get("count", 50))
        dim_property = self.generate_properties(dim_destination)
        dim_route = self.generate_routes(dim_destination)
        fact_supplier_terms = self.generate_supplier_terms(dim_property, dim_route, dim_supplier)
        fact_external_signals = self.generate_external_signals(dim_calendar, dim_destination)

        fact_bookings, fact_searches, fact_soldouts = self.generate_market_transactions(
            dim_calendar, dim_destination, dim_property, dim_route, fact_supplier_terms
        )

        datasets = {
            "dim_calendar": dim_calendar,
            "dim_destination": dim_destination,
            "dim_supplier": dim_supplier,
            "dim_property": dim_property,
            "dim_route": dim_route,
            "fact_supplier_terms": fact_supplier_terms,
            "fact_external_signals": fact_external_signals,
            "fact_searches": fact_searches,
            "fact_bookings": fact_bookings,
            "fact_soldouts": fact_soldouts,
        }

        # Persist raw CSV files
        for name, df in datasets.items():
            csv_file = out_path / f"{name}.csv"
            df.to_csv(csv_file, index=False)
            logger.info("Persisted synthetic table", table=name, rows=len(df), path=str(csv_file))

        # Persist ground-truth parameters JSON
        ground_truth = {
            "seed": self.seed,
            "start_date": str(self.start_date),
            "end_date": str(self.end_date),
            "num_destinations": len(dim_destination),
            "num_suppliers": len(dim_supplier),
            "num_hotels": len(dim_property),
            "num_routes": len(dim_route),
            "ground_truth_effects": self.config.get("ground_truth_effects", {}),
        }
        with open(out_path / "ground_truth_parameters.json", "w", encoding="utf-8") as f:
            json.dump(ground_truth, f, indent=2)

        logger.info("Saved ground truth parameters for model recovery checks", path=str(out_path / "ground_truth_parameters.json"))
        return datasets


if __name__ == "__main__":
    generator = SyntheticDataGenerator()
    generator.generate_all_datasets()
