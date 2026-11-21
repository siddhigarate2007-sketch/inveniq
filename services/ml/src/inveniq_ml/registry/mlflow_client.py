"""Model Registry and Champion-Challenger Promotion Engine for InvenIQ."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any
import structlog

logger = structlog.get_logger(__name__)


class ModelRegistry:
    """Manages versioned model artifacts and champion-challenger promotion rules."""

    def __init__(self, registry_file: Path | str | None = None) -> None:
        if registry_file:
            self.registry_path = Path(registry_file)
        else:
            cur = Path(__file__).resolve().parent
            repo_root = cur
            for p in cur.parents:
                if (p / "pyproject.toml").exists():
                    repo_root = p
                    break
            self.registry_path = repo_root / "data" / "models" / "registry.json"

        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.registry_path.exists():
            self._save_registry({
                "models": {},
                "production_champion": None,
                "history": [],
            })

    def _load_registry(self) -> dict[str, Any]:
        with open(self.registry_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_registry(self, data: dict[str, Any]) -> None:
        with open(self.registry_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def register_model_run(
        self,
        model_name: str,
        version: str,
        metrics: dict[str, float],
        parameters: dict[str, Any],
        artifact_uri: str = "",
    ) -> dict[str, Any]:
        """Registers a newly trained model run with metrics and parameters."""
        data = self._load_registry()
        model_id = f"{model_name}:{version}"

        entry = {
            "model_id": model_id,
            "model_name": model_name,
            "version": version,
            "registered_at": datetime.utcnow().isoformat(),
            "stage": "Staging",
            "metrics": metrics,
            "parameters": parameters,
            "artifact_uri": artifact_uri,
        }
        data["models"][model_id] = entry
        data["history"].append({
            "action": "REGISTER",
            "model_id": model_id,
            "timestamp": entry["registered_at"],
        })
        self._save_registry(data)
        logger.info("Model registered in staging", model_id=model_id, wmape=metrics.get("wmape"))
        return entry

    def evaluate_champion_challenger(
        self,
        challenger_model_id: str,
        metric_key: str = "wmape",
        min_relative_improvement: float = 0.02,
    ) -> bool:
        """Evaluates whether the challenger should be promoted over the active champion."""
        data = self._load_registry()
        champion_id = data.get("production_champion")

        if challenger_model_id not in data["models"]:
            raise ValueError(f"Challenger {challenger_model_id} not found in registry.")

        challenger = data["models"][challenger_model_id]
        challenger_metric = challenger["metrics"].get(metric_key, float("inf"))

        if champion_id is None:
            # No champion currently: auto-promote
            challenger["stage"] = "Production"
            data["production_champion"] = challenger_model_id
            data["history"].append({
                "action": "PROMOTED_INITIAL",
                "model_id": challenger_model_id,
                "timestamp": datetime.utcnow().isoformat(),
            })
            self._save_registry(data)
            logger.info("Challenger promoted to initial champion", champion=challenger_model_id)
            return True

        champion = data["models"][champion_id]
        champion_metric = champion["metrics"].get(metric_key, float("inf"))

        # For WMAPE, lower is better
        rel_improvement = (champion_metric - challenger_metric) / max(1e-6, champion_metric)

        if rel_improvement >= min_relative_improvement:
            champion["stage"] = "Archived"
            challenger["stage"] = "Production"
            data["production_champion"] = challenger_model_id
            data["history"].append({
                "action": "PROMOTED_CHAMPION",
                "challenger": challenger_model_id,
                "previous_champion": champion_id,
                "relative_improvement": round(rel_improvement, 4),
                "timestamp": datetime.utcnow().isoformat(),
            })
            self._save_registry(data)
            logger.info(
                "Challenger promoted over Champion",
                new_champion=challenger_model_id,
                previous_champion=champion_id,
                improvement_pct=round(rel_improvement * 100, 2),
            )
            return True
        else:
            logger.info(
                "Challenger failed to outperform Champion",
                challenger=challenger_model_id,
                champion=champion_id,
                improvement_pct=round(rel_improvement * 100, 2),
            )
            return False
