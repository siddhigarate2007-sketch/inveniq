"""Prometheus metrics exporter and collector for InvenIQ."""

import threading
import time
from typing import Any


class MetricsCollector:
    """Thread-safe Prometheus metrics collector for InvenIQ."""

    _instance: "MetricsCollector | None" = None
    _lock = threading.Lock()

    def __new__(cls) -> "MetricsCollector":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init_metrics()
            return cls._instance

    def _init_metrics(self) -> None:
        self.lock = threading.Lock()
        self.http_requests_total: dict[tuple[str, str, int], int] = {}
        self.http_duration_sum: dict[tuple[str, str], float] = {}
        self.http_duration_count: dict[tuple[str, str], int] = {}

        self.optimization_runs_total: dict[tuple[str, str], int] = {}
        self.optimization_duration_sum: float = 0.0
        self.optimization_duration_count: int = 0

        self.last_budget_allocated_inr: float = 0.0
        self.last_expected_profit_inr: float = 0.0
        self.last_cvar_risk_inr: float = 0.0
        self.last_solve_gap: float = 0.0

    def record_request(self, method: str, path: str, status_code: int, duration_seconds: float) -> None:
        with self.lock:
            key = (method, path, status_code)
            self.http_requests_total[key] = self.http_requests_total.get(key, 0) + 1

            path_key = (method, path)
            self.http_duration_sum[path_key] = self.http_duration_sum.get(path_key, 0.0) + duration_seconds
            self.http_duration_count[path_key] = self.http_duration_count.get(path_key, 0) + 1

    def record_optimization_run(
        self,
        status: str,
        risk_appetite: str,
        duration_seconds: float,
        budget_inr: float,
        profit_inr: float,
        cvar_inr: float,
    ) -> None:
        with self.lock:
            run_key = (status, risk_appetite)
            self.optimization_runs_total[run_key] = self.optimization_runs_total.get(run_key, 0) + 1
            self.optimization_duration_sum += duration_seconds
            self.optimization_duration_count += 1
            self.last_budget_allocated_inr = budget_inr
            self.last_expected_profit_inr = profit_inr
            self.last_cvar_risk_inr = cvar_inr

    def export_prometheus_text(self) -> str:
        """Serializes current in-memory counters to Prometheus exposition format."""
        lines: list[str] = [
            "# HELP inveniq_http_requests_total Total number of HTTP requests processed by InvenIQ API.",
            "# TYPE inveniq_http_requests_total counter",
        ]
        with self.lock:
            for (method, path, status), count in self.http_requests_total.items():
                lines.append(f'inveniq_http_requests_total{{method="{method}",path="{path}",status="{status}"}} {count}')

            lines.append("# HELP inveniq_http_request_duration_seconds HTTP request latency summary in seconds.")
            lines.append("# TYPE inveniq_http_request_duration_seconds summary")
            for (method, path), total_dur in self.http_duration_sum.items():
                cnt = self.http_duration_count.get((method, path), 1)
                lines.append(f'inveniq_http_request_duration_seconds_sum{{method="{method}",path="{path}"}} {total_dur:.4f}')
                lines.append(f'inveniq_http_request_duration_seconds_count{{method="{method}",path="{path}"}} {cnt}')

            lines.append("# HELP inveniq_optimization_runs_total Total number of stochastic MILP runs dispatched.")
            lines.append("# TYPE inveniq_optimization_runs_total counter")
            for (status, appetite), count in self.optimization_runs_total.items():
                lines.append(f'inveniq_optimization_runs_total{{status="{status}",risk_appetite="{appetite}"}} {count}')

            lines.append("# HELP inveniq_optimization_solve_duration_seconds Execution time of HiGHS MILP solver.")
            lines.append("# TYPE inveniq_optimization_solve_duration_seconds summary")
            lines.append(f"inveniq_optimization_solve_duration_seconds_sum {self.optimization_duration_sum:.4f}")
            lines.append(f"inveniq_optimization_solve_duration_seconds_count {self.optimization_duration_count}")

            lines.append("# HELP inveniq_budget_allocated_inr Total committed capital budget in INR for latest run.")
            lines.append("# TYPE inveniq_budget_allocated_inr gauge")
            lines.append(f"inveniq_budget_allocated_inr {self.last_budget_allocated_inr}")

            lines.append("# HELP inveniq_expected_profit_inr Expected net portfolio profit in INR for latest run.")
            lines.append("# TYPE inveniq_expected_profit_inr gauge")
            lines.append(f"inveniq_expected_profit_inr {self.last_expected_profit_inr}")

            lines.append("# HELP inveniq_cvar_risk_inr 95% CVaR tail risk in INR for latest run.")
            lines.append("# TYPE inveniq_cvar_risk_inr gauge")
            lines.append(f"inveniq_cvar_risk_inr {self.last_cvar_risk_inr}")

        return "\n".join(lines) + "\n"


metrics_collector = MetricsCollector()
