"""End-to-end training and evaluation pipeline for demand forecasting."""

from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd
import structlog
from inveniq_ml.features.builder import FeaturePipeline
from inveniq_ml.forecasting.baselines import RollingMeanForecaster, SeasonalNaiveForecaster
from inveniq_ml.forecasting.conformal import ConformalQuantileCalibrator
from inveniq_ml.forecasting.evaluation import ForecastEvaluator
from inveniq_ml.forecasting.lightgbm_model import QuantileLightGBMForecaster

logger = structlog.get_logger(__name__)


class DemandForecastingPipeline:
    """Orchestrates feature extraction, training, conformal calibration, and evaluation."""

    def __init__(self, lakehouse_db_path: Path | str | None = None) -> None:
        self.feature_pipeline = FeaturePipeline(lakehouse_db_path=lakehouse_db_path)
        self.evaluator = ForecastEvaluator()
        self.lgbm_forecaster = QuantileLightGBMForecaster()
        self.conformal_calibrator = ConformalQuantileCalibrator(desired_coverage=0.80)

    def run_pipeline(self) -> dict[str, Any]:
        """Runs feature engineering, temporal split, model fitting, and evaluation."""
        logger.info("Starting demand forecasting training and evaluation pipeline")

        # 1. Feature Extraction & Engineering
        df_featured, feature_cols, target_col = self.feature_pipeline.prepare_dataset()

        # 2. Rolling-Origin Temporal Split (Walk-forward split)
        # Train: 2023-01-01 to 2024-06-30
        # Calibration: 2024-07-01 to 2024-12-31
        # Test: 2025-01-01 to 2025-12-31
        dates = pd.to_datetime(df_featured["travel_date"])
        train_mask = dates < "2024-07-01"
        cal_mask = (dates >= "2024-07-01") & (dates < "2025-01-01")
        test_mask = dates >= "2025-01-01"

        df_train = df_featured[train_mask].copy()
        df_cal = df_featured[cal_mask].copy()
        df_test = df_featured[test_mask].copy()

        logger.info(
            "Temporal splits established",
            train_rows=len(df_train),
            cal_rows=len(df_cal),
            test_rows=len(df_test),
        )

        # 3. Fit Baselines
        logger.info("Fitting baseline forecasters")
        naive_model = SeasonalNaiveForecaster(lag=7).fit(df_train, target_col)
        naive_preds = naive_model.predict(df_test)

        rolling_model = RollingMeanForecaster(window=14).fit(df_train, target_col)
        rolling_preds = rolling_model.predict(df_test)

        # 4. Train Main Quantile LightGBM
        logger.info("Training Global Quantile LightGBM models")
        self.lgbm_forecaster.fit(
            X_train=df_train[feature_cols],
            y_train=df_train[target_col],
            feature_names=feature_cols,
        )

        # 5. Conformal Calibration on Calibration Fold
        logger.info("Running Conformal Quantile Calibration")
        cal_preds = self.lgbm_forecaster.predict_quantiles(df_cal[feature_cols])
        adjustment = self.conformal_calibrator.calibrate(
            y_true=df_cal[target_col],
            q10_pred=cal_preds["q_10"],
            q90_pred=cal_preds["q_90"],
        )

        # 6. Inference on Out-of-Time Test Set (2025)
        raw_test_preds = self.lgbm_forecaster.predict_quantiles(df_test[feature_cols])
        q10_cal, q90_cal = self.conformal_calibrator.adjust_intervals(
            q10_pred=raw_test_preds["q_10"],
            q90_pred=raw_test_preds["q_90"],
        )
        df_test_eval = df_test.copy()
        df_test_eval["q_10_raw"] = raw_test_preds["q_10"]
        df_test_eval["q_50"] = raw_test_preds["q_50"]
        df_test_eval["q_90_raw"] = raw_test_preds["q_90"]
        df_test_eval["q_10_conformal"] = q10_cal
        df_test_eval["q_90_conformal"] = q90_cal

        # 7. Evaluate Metrics Across Models
        y_test = df_test[target_col].to_numpy()

        metrics_naive = {
            "wmape": round(self.evaluator.wmape(y_test, naive_preds), 4),
            "smape": round(self.evaluator.smape(y_test, naive_preds), 2),
            "bias": round(self.evaluator.forecast_bias(y_test, naive_preds), 4),
        }
        metrics_rolling = {
            "wmape": round(self.evaluator.wmape(y_test, rolling_preds), 4),
            "smape": round(self.evaluator.smape(y_test, rolling_preds), 2),
            "bias": round(self.evaluator.forecast_bias(y_test, rolling_preds), 4),
        }
        metrics_lgbm_raw = self.evaluator.evaluate_all(
            y_true=y_test,
            q10=raw_test_preds["q_10"].to_numpy(),
            q50=raw_test_preds["q_50"].to_numpy(),
            q90=raw_test_preds["q_90"].to_numpy(),
        )
        metrics_lgbm_conformal = self.evaluator.evaluate_all(
            y_true=y_test,
            q10=q10_cal,
            q50=raw_test_preds["q_50"].to_numpy(),
            q90=q90_cal,
        )

        # 8. Segment-wise Evaluation Breakdown
        df_segment_eval = self.evaluator.evaluate_by_segments(
            df_results=df_test_eval,
            segment_cols=["product_type", "domestic_flag"],
            y_col=target_col,
            q10_col="q_10_conformal",
            q50_col="q_50",
            q90_col="q_90_conformal",
        )

        # 9. Verify Ground-Truth Recovery (Seasonality and Festivals)
        fest_mask = df_test_eval["is_festival"] == 1
        non_fest_mask = df_test_eval["is_festival"] == 0
        avg_pred_fest = float(df_test_eval[fest_mask]["q_50"].mean())
        avg_pred_non_fest = float(df_test_eval[non_fest_mask]["q_50"].mean())
        festival_lift_recovered = (avg_pred_fest / avg_pred_non_fest) - 1.0

        feature_importances = self.lgbm_forecaster.get_feature_importances().head(10).to_dict(orient="records")

        report = {
            "status": "SUCCESS",
            "test_sample_size": len(df_test),
            "conformal_adjustment": round(adjustment, 3),
            "baselines": {
                "seasonal_naive": metrics_naive,
                "rolling_mean": metrics_rolling,
            },
            "lightgbm_raw": metrics_lgbm_raw,
            "lightgbm_conformal": metrics_lgbm_conformal,
            "segment_breakdown": df_segment_eval.to_dict(orient="records"),
            "ground_truth_recovery": {
                "festival_lift_recovered_pct": round(festival_lift_recovered * 100, 1),
                "is_lift_captured": festival_lift_recovered > 0.30,
            },
            "top_features": feature_importances,
        }

        logger.info(
            "Forecasting evaluation report completed",
            wmape_lgbm=metrics_lgbm_conformal["wmape"],
            wmape_naive=metrics_naive["wmape"],
            conformal_coverage=metrics_lgbm_conformal["coverage_80"],
        )
        return report


if __name__ == "__main__":
    pipeline = DemandForecastingPipeline()
    report = pipeline.run_pipeline()
    print("Forecasting Pipeline Report:")
    print("WMAPE LightGBM:", report["lightgbm_conformal"]["wmape"], "vs Naive:", report["baselines"]["seasonal_naive"]["wmape"])
    print("Conformal 80% Coverage:", report["lightgbm_conformal"]["coverage_80"])
    print("Festival Lift Recovered:", report["ground_truth_recovery"]["festival_lift_recovered_pct"], "%")
