"""In-memory thread-safe state store and database provider for InvenIQ."""

import hashlib
import threading
from datetime import datetime
from pathlib import Path
from typing import Any
import duckdb
import pandas as pd
import structlog
from inveniq_core.schemas.optimization import OptimizationRunResponse, RunStatus
from inveniq_core.schemas.user import AuditLogEntry, UserInDB, UserRole

logger = structlog.get_logger(__name__)


def hash_password(password: str) -> str:
    """Produces SHA-256 salted hash of password."""
    salt = "tbo-inveniq-security-salt-2026"
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


class DBStore:
    """Thread-safe storage singleton for Users, Optimization Runs, and Audit Logs."""

    _instance: "DBStore | None" = None
    _lock = threading.Lock()

    def __new__(cls) -> "DBStore":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init_store()
            return cls._instance

    def _init_store(self) -> None:
        self.lock = threading.Lock()
        self.users: dict[str, UserInDB] = {}
        self.runs: dict[str, OptimizationRunResponse] = {}
        self.idempotency_map: dict[str, str] = {}  # idempotency_key -> run_id
        self.audit_logs: list[AuditLogEntry] = []

        # Seed standard demo users
        default_pwd_hash = hash_password("InvenIQ2026!")

        demo_users = [
            UserInDB(
                user_id="USR_BUYER_01",
                email="buyer@tbo.com",
                full_name="Rajesh Sharma (Procurement Lead)",
                role=UserRole.BUYER,
                hashed_password=default_pwd_hash,
            ),
            UserInDB(
                user_id="USR_ANALYST_01",
                email="analyst@tbo.com",
                full_name="Priya Patel (Revenue Analyst)",
                role=UserRole.ANALYST,
                hashed_password=default_pwd_hash,
            ),
            UserInDB(
                user_id="USR_FINANCE_01",
                email="finance@tbo.com",
                full_name="Vikramaditya Sengupta (Head of Risk & Finance)",
                role=UserRole.FINANCE_APPROVER,
                hashed_password=default_pwd_hash,
            ),
            UserInDB(
                user_id="USR_ADMIN_01",
                email="admin@tbo.com",
                full_name="Antigravity System Admin",
                role=UserRole.ADMIN,
                hashed_password=default_pwd_hash,
            ),
        ]
        for u in demo_users:
            self.users[u.email.lower()] = u

        logger.info("DBStore initialized with default demo roles", users_count=len(self.users))

    def get_user_by_email(self, email: str) -> UserInDB | None:
        return self.users.get(email.lower().strip())

    def get_user_by_id(self, user_id: str) -> UserInDB | None:
        for u in self.users.values():
            if u.user_id == user_id:
                return u
        return None

    def save_run(self, run: OptimizationRunResponse) -> None:
        with self.lock:
            self.runs[run.run_id] = run
            if run.idempotency_key:
                self.idempotency_map[run.idempotency_key] = run.run_id

    def get_run(self, run_id: str) -> OptimizationRunResponse | None:
        with self.lock:
            return self.runs.get(run_id)

    def get_run_by_idempotency_key(self, key: str) -> OptimizationRunResponse | None:
        with self.lock:
            run_id = self.idempotency_map.get(key)
            if run_id:
                return self.runs.get(run_id)
            return None

    def list_runs(self, limit: int = 50, offset: int = 0) -> list[OptimizationRunResponse]:
        with self.lock:
            all_runs = sorted(self.runs.values(), key=lambda r: r.created_at, reverse=True)
            return all_runs[offset : offset + limit]

    def record_audit(
        self,
        user_id: str,
        user_email: str,
        user_role: UserRole,
        action: str,
        target_type: str,
        target_id: str,
        details: dict[str, Any] | None = None,
    ) -> AuditLogEntry:
        with self.lock:
            entry = AuditLogEntry(
                audit_id=f"AUD_{len(self.audit_logs) + 1:06d}",
                user_id=user_id,
                user_email=user_email,
                user_role=user_role,
                action=action,
                target_type=target_type,
                target_id=target_id,
                details=details or {},
            )
            self.audit_logs.append(entry)
            logger.info("Audit log recorded", action=action, user=user_email, target_id=target_id)
            return entry

    def list_audit_logs(self, limit: int = 100) -> list[AuditLogEntry]:
        with self.lock:
            return sorted(self.audit_logs, key=lambda a: a.timestamp, reverse=True)[:limit]

    def load_candidates_for_optimization(self) -> pd.DataFrame:
        """Loads representative candidate inventory from DuckDB lakehouse."""
        # Locate lakehouse DB
        cur = Path(__file__).resolve().parent
        repo_root = cur
        for p in cur.parents:
            if (p / "data" / "lakehouse" / "inveniq_lake.duckdb").exists():
                repo_root = p
                break
        db_path = repo_root / "data" / "lakehouse" / "inveniq_lake.duckdb"

        if db_path.exists():
            con = duckdb.connect(str(db_path), read_only=True)
            query = """
            SELECT 
                t.entity_id,
                p.destination_id,
                'HOTEL' as product_type,
                t.supplier_id,
                t.unit_cost_inr as cost_price_inr,
                ROUND(t.unit_cost_inr * 1.30, 2) as sell_price_inr,
                t.allotment_size,
                t.min_order_qty,
                t.release_cutoff_days,
                s.reliability_score,
                20.0 as q_10,
                35.0 as q_50,
                55.0 as q_90,
                0.06 as cancel_prob
            FROM fact_supplier_terms t
            JOIN dim_property p ON t.entity_id = p.property_id
            JOIN dim_supplier s ON t.supplier_id = s.supplier_id
            LIMIT 25;
            """
            try:
                df = con.execute(query).df()
                con.close()
                if not df.empty:
                    return df
            except Exception as e:
                logger.warning("Falling back to synthetic candidate generation", error=str(e))

        # Fallback candidate pool if lakehouse not loaded
        return pd.DataFrame([
            {
                "entity_id": f"HTL_GOA_{i:03d}",
                "destination_id": "DEST_GOA",
                "product_type": "HOTEL",
                "supplier_id": f"SUP_{i % 5 + 1:03d}",
                "cost_price_inr": 5000.0 + i * 500.0,
                "sell_price_inr": 7200.0 + i * 700.0,
                "allotment_size": 40,
                "min_order_qty": 3,
                "release_cutoff_days": 14,
                "reliability_score": 0.95,
                "q_10": 20.0,
                "q_50": 35.0,
                "q_90": 55.0,
                "cancel_prob": 0.06,
            }
            for i in range(15)
        ] + [
            {
                "entity_id": f"HTL_DXB_{i:03d}",
                "destination_id": "DEST_DUBAI",
                "product_type": "HOTEL",
                "supplier_id": f"SUP_{i % 5 + 1:03d}",
                "cost_price_inr": 12000.0 + i * 1000.0,
                "sell_price_inr": 16500.0 + i * 1400.0,
                "allotment_size": 30,
                "min_order_qty": 4,
                "release_cutoff_days": 21,
                "reliability_score": 0.97,
                "q_10": 15.0,
                "q_50": 28.0,
                "q_90": 42.0,
                "cancel_prob": 0.05,
            }
            for i in range(10)
        ])


db_store = DBStore()
