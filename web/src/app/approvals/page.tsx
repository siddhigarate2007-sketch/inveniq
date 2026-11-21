"use client";

import React, { useEffect, useState } from "react";
import {
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Clock,
  User,
  AlertTriangle,
  FileText,
  Lock,
  ArrowRight,
} from "lucide-react";
import { api } from "@/lib/api";
import { formatDateTime, formatINR, getStatusBadgeClass } from "@/lib/formatters";
import { AuditLogEntry, OptimizationRunResponse, UserRole } from "@/lib/types";

export default function ApprovalsAndAuditPage() {
  const [currentUser, setCurrentUser] = useState(api.getCurrentUser());
  const [runs, setRuns] = useState<OptimizationRunResponse[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  // Approval Action Dialog State
  const [selectedRun, setSelectedRun] = useState<OptimizationRunResponse | null>(null);
  const [approvalNote, setApprovalNote] = useState<string>("");
  const [isApproving, setIsApproving] = useState<boolean>(false);

  useEffect(() => {
    loadData();
    const handleRoleChanged = () => {
      setCurrentUser(api.getCurrentUser());
      loadData();
    };
    window.addEventListener("roleChanged", handleRoleChanged);
    return () => window.removeEventListener("roleChanged", handleRoleChanged);
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [allRuns, logs] = await Promise.all([
        api.listRuns(),
        api.getAuditTrail(),
      ]);
      setRuns(allRuns);
      setAuditLogs(logs);
      setCurrentUser(api.getCurrentUser());
    } finally {
      setLoading(false);
    }
  };

  const isFinanceOrAdmin =
    currentUser.role === "finance_approver" || currentUser.role === "admin";

  const pendingRuns = runs.filter(
    (r) => r.status === "COMPLETED_AWAITING_APPROVAL"
  );

  const handleApprovalAction = async (approved: boolean) => {
    if (!selectedRun) return;
    setIsApproving(true);
    try {
      await api.approveOrRejectRun(selectedRun.run_id, {
        approved,
        notes:
          approvalNote ||
          (approved
            ? "Approved: Pre-buy inventory commitments authorized."
            : "Rejected by Finance Approver"),
      });
      setSelectedRun(null);
      setApprovalNote("");
      await loadData();
    } finally {
      setIsApproving(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Title */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-slate-100 flex items-center space-x-3">
            <span>Corporate Approvals & Governance Audit Trail</span>
            <span className="text-xs px-2.5 py-0.5 rounded-full font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
              SOC2 & ISO Compliant
            </span>
          </h1>
          <p className="text-xs md:text-sm text-slate-400 mt-1">
            Financial sign-offs for multi-crore capital commitments with immutable audit log records.
          </p>
        </div>

        <div className="flex items-center space-x-2 text-xs">
          <span className="text-slate-400">Authenticated Persona:</span>
          <span className="px-2.5 py-1 rounded-lg font-semibold bg-slate-800 text-tbo-300 border border-slate-700 uppercase">
            {currentUser.full_name} ({currentUser.role.replace("_", " ")})
          </span>
        </div>
      </div>

      {/* Role Notice Banner */}
      {!isFinanceOrAdmin && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-950/20 p-4 flex items-start space-x-3 text-xs text-amber-300">
          <AlertTriangle className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="font-bold">Read-Only Governance Access</p>
            <p className="text-slate-300 text-[11px] leading-relaxed">
              You are currently viewing InvenIQ as <strong>{currentUser.role.replace("_", " ")}</strong>. Approval and rejection actions require <strong>Finance Approver</strong> or <strong>Admin</strong> privileges. Use the Role Switcher in the top-right header to switch roles for demonstration.
            </p>
          </div>
        </div>
      )}

      {/* Section 1: Pending Procurement Runs Requiring Financial Authorization */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center space-x-2">
            <ShieldCheck className="h-5 w-5 text-amber-400" />
            <h2 className="text-sm font-bold text-slate-100">
              Procurement Runs Awaiting Financial Authorization ({pendingRuns.length})
            </h2>
          </div>
          <span className="text-[11px] text-slate-400">
            Sign-Off Threshold: &ge; ₹1.0 Cr
          </span>
        </div>

        {pendingRuns.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-400 space-y-2">
            <CheckCircle2 className="h-8 w-8 text-emerald-400 mx-auto" />
            <p className="font-semibold text-slate-300">
              All inventory procurement runs have been reviewed.
            </p>
            <p className="text-[11px]">No pending capital commitments in queue.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {pendingRuns.map((run) => (
              <div
                key={run.run_id}
                className="rounded-xl border border-amber-500/30 bg-slate-900/90 p-5 space-y-4"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <span className="font-mono font-bold text-sm text-slate-100">
                        {run.run_id}
                      </span>
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/15 text-amber-300 border border-amber-500/30">
                        Pending Sign-Off
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400">
                      Requested by <strong className="text-slate-300">{run.created_by_user_id}</strong> on {formatDateTime(run.created_at)}
                    </p>
                  </div>

                  {/* Actions for Finance Approver */}
                  {isFinanceOrAdmin && (
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => setSelectedRun(run)}
                        className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center space-x-1.5 transition shadow"
                      >
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        <span>Authorize Purchase</span>
                      </button>
                      <button
                        onClick={() => setSelectedRun(run)}
                        className="px-3 py-1.5 rounded-lg border border-rose-500/40 bg-rose-950/20 hover:bg-rose-900/40 text-rose-300 text-xs font-semibold flex items-center space-x-1.5 transition"
                      >
                        <XCircle className="h-3.5 w-3.5" />
                        <span>Reject</span>
                      </button>
                    </div>
                  )}
                </div>

                {/* Financial Summary Strip */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 border-t border-slate-800 text-xs">
                  <div>
                    <span className="text-[10px] text-slate-400">Capital Commitment:</span>
                    <p className="font-bold text-blue-400">
                      {formatINR(run.total_capital_committed_inr || run.budget_inr, true)}
                    </p>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400">Expected Profit / ROI:</span>
                    <p className="font-bold text-emerald-400">
                      {formatINR(run.expected_profit_inr, true)} ({run.expected_roi_pct?.toFixed(1)}%)
                    </p>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400">CVaR 95% Tail Risk:</span>
                    <p className="font-bold text-rose-400">
                      {formatINR(run.cvar_alpha_loss_inr, true)}
                    </p>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400">Risk Profile:</span>
                    <p className="font-bold text-slate-200">
                      {run.risk_appetite}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Approval / Rejection Modal Dialog */}
      {selectedRun && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-2xl border border-slate-700 bg-navy-900 p-6 space-y-4 shadow-2xl animate-in zoom-in-95 duration-150">
            <h3 className="text-base font-bold text-slate-100 flex items-center space-x-2">
              <ShieldCheck className="h-5 w-5 text-tbo-400" />
              <span>Financial Sign-Off: {selectedRun.run_id}</span>
            </h3>

            <p className="text-xs text-slate-300">
              You are about to authorize capital commitment of{" "}
              <strong className="text-emerald-400">
                {formatINR(selectedRun.total_capital_committed_inr || selectedRun.budget_inr, true)}
              </strong>{" "}
              across {selectedRun.recommendations.length} inventory pre-buy blocks.
            </p>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300">
                Approver Audit Notes & Sign-Off Justification:
              </label>
              <textarea
                value={approvalNote}
                onChange={(e) => setApprovalNote(e.target.value)}
                placeholder="e.g. Authorized under Q4 seasonal marketing budget allocation."
                className="w-full h-20 px-3 py-2 rounded-lg border border-slate-700 bg-slate-800 text-xs text-slate-200 focus:outline-none focus:border-tbo-500"
              />
            </div>

            <div className="flex items-center justify-end space-x-3 pt-2">
              <button
                onClick={() => setSelectedRun(null)}
                className="px-4 py-2 rounded-lg text-xs font-semibold text-slate-400 hover:text-slate-200 transition"
              >
                Cancel
              </button>
              <button
                onClick={() => handleApprovalAction(false)}
                disabled={isApproving}
                className="px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold transition"
              >
                Reject Commitments
              </button>
              <button
                onClick={() => handleApprovalAction(true)}
                disabled={isApproving}
                className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition"
              >
                Approve & Execute
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Section 2: Immutable Governance Audit Log Trail */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 overflow-hidden shadow-xl">
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Lock className="h-4 w-4 text-emerald-400" />
            <h2 className="text-sm font-bold text-slate-200">
              Immutable Governance Audit Log Trail
            </h2>
          </div>
          <span className="text-[11px] text-slate-400">
            Append-Only Compliance Ledger
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950/80 text-[11px] uppercase tracking-wider text-slate-400 border-b border-slate-800 font-semibold">
              <tr>
                <th className="py-3 px-4">Audit ID</th>
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4">User & Role</th>
                <th className="py-3 px-4">Action</th>
                <th className="py-3 px-4">Target Run</th>
                <th className="py-3 px-4">Governance Notes / Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {auditLogs.map((log) => (
                <tr key={log.audit_id} className="hover:bg-slate-800/40 transition">
                  <td className="py-3.5 px-4 font-mono font-bold text-slate-400 text-[11px]">
                    {log.audit_id}
                  </td>
                  <td className="py-3.5 px-4 whitespace-nowrap text-slate-300">
                    {formatDateTime(log.timestamp)}
                  </td>
                  <td className="py-3.5 px-4">
                    <p className="font-semibold text-slate-200">{log.user_email}</p>
                    <p className="text-[10px] uppercase text-tbo-400 font-mono">
                      {log.user_role}
                    </p>
                  </td>
                  <td className="py-3.5 px-4">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                        log.action.includes("APPROVE")
                          ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/30"
                          : log.action.includes("REJECT")
                          ? "bg-rose-500/15 text-rose-300 border-rose-500/30"
                          : "bg-blue-500/15 text-blue-300 border-blue-500/30"
                      }`}
                    >
                      {log.action}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 font-mono text-slate-300">
                    {log.target_id}
                  </td>
                  <td className="py-3.5 px-4 text-slate-400 text-[11px] max-w-sm">
                    {log.details?.notes ? (
                      <span className="italic text-slate-300">
                        &quot;{log.details.notes}&quot;
                      </span>
                    ) : (
                      <code>{JSON.stringify(log.details)}</code>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
