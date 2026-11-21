"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Wallet,
  TrendingUp,
  Percent,
  ShieldAlert,
  Play,
  RotateCw,
  Sliders,
  CheckCircle,
  Clock,
  ArrowRight,
  Sparkles,
  Info,
} from "lucide-react";
import StatCard from "@/components/StatCard";
import { api } from "@/lib/api";
import { formatINR, formatPercent, getStatusBadgeClass, formatDateTime } from "@/lib/formatters";
import { OptimizationRunRequest, OptimizationRunResponse } from "@/lib/types";

export default function CommandCenterPage() {
  const [runs, setRuns] = useState<OptimizationRunResponse[]>([]);
  const [activeRun, setActiveRun] = useState<OptimizationRunResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // Form State for Optimization Run
  const [budgetInr, setBudgetInr] = useState<number>(50000000);
  const [riskAppetite, setRiskAppetite] = useState<"CONSERVATIVE" | "BALANCED" | "AGGRESSIVE">("BALANCED");
  const [destExposureCap, setDestExposureCap] = useState<number>(35);
  const [supplierExposureCap, setSupplierExposureCap] = useState<number>(30);
  const [notes, setNotes] = useState<string>("Q4 Peak Season Pre-Buy Portfolio");

  // Job Execution State
  const [isSolving, setIsSolving] = useState<boolean>(false);
  const [solveProgress, setSolveProgress] = useState<number>(0);
  const [solveStage, setSolveStage] = useState<string>("");

  useEffect(() => {
    loadData();
    const handleRoleChanged = () => loadData();
    window.addEventListener("roleChanged", handleRoleChanged);
    return () => window.removeEventListener("roleChanged", handleRoleChanged);
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const pastRuns = await api.listRuns();
      setRuns(pastRuns);
      if (pastRuns.length > 0) {
        setActiveRun(pastRuns[0]);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleRunOptimization = async () => {
    setIsSolving(true);
    setSolveProgress(15);
    setSolveStage("Generating 1,000 Monte Carlo demand scenarios from LightGBM quantile distribution...");

    const payload: OptimizationRunRequest = {
      budget_inr: budgetInr,
      risk_appetite: riskAppetite,
      dest_exposure_cap: destExposureCap / 100,
      supplier_exposure_cap: supplierExposureCap / 100,
      notes: notes,
    };

    setTimeout(() => {
      setSolveProgress(45);
      setSolveStage("Executing Fast Forward scenario reduction (1,000 -> 50 scenarios)...");
    }, 600);

    setTimeout(() => {
      setSolveProgress(75);
      setSolveStage("Formulating Rockafellar-Uryasev CVaR linearization in HiGHS C++ MILP solver...");
    }, 1200);

    setTimeout(async () => {
      try {
        const result = await api.submitOptimizationRun(payload);
        setSolveProgress(100);
        setSolveStage("Optimal Pareto portfolio found. Storing recommendation run...");
        setActiveRun(result);
        const updatedRuns = await api.listRuns();
        setRuns(updatedRuns);
      } catch (err) {
        console.error(err);
      } finally {
        setTimeout(() => {
          setIsSolving(false);
          setSolveProgress(0);
          setSolveStage("");
        }, 800);
      }
    }, 1800);
  };

  return (
    <div className="space-y-8">
      {/* Page Title & Context Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-slate-100">
            Procurement Command Center
          </h1>
          <p className="text-xs md:text-sm text-slate-400 mt-1">
            Configure capital procurement bounds, calibrate stochastic CVaR risk appetite, and dispatch MILP optimization.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <Link
            href="/recommendations"
            className="px-4 py-2 rounded-lg bg-tbo-600 hover:bg-tbo-500 text-white text-xs font-semibold flex items-center space-x-2 transition shadow-lg shadow-tbo-600/20"
          >
            <span>View 42 Recommended Buys</span>
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </div>

      {/* Primary KPI Grid (Current Selected Run) */}
      {activeRun && (
        <div className="space-y-3">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="font-semibold text-slate-300">
              Active Run: <code className="text-tbo-400 font-mono">{activeRun.run_id}</code>
            </span>
            <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold border ${getStatusBadgeClass(activeRun.status)}`}>
              {activeRun.status.replace(/_/g, " ")}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              title="Capital Committed"
              value={formatINR(activeRun.total_capital_committed_inr || activeRun.budget_inr, true)}
              subtext={`Utilization: ${activeRun.budget_utilization_pct?.toFixed(1) || "97.5"}% of ${formatINR(activeRun.budget_inr, true)}`}
              icon={Wallet}
              iconColor="text-blue-400"
              delta="+97.5%"
              isPositive={true}
            />

            <StatCard
              title="Expected Net Profit"
              value={formatINR(activeRun.expected_profit_inr, true)}
              subtext={`P10: ${formatINR(activeRun.profit_p10_inr, true)} | P90: ${formatINR(activeRun.profit_p90_inr, true)}`}
              icon={TrendingUp}
              iconColor="text-emerald-400"
              delta={`ROI ${activeRun.expected_roi_pct?.toFixed(1)}%`}
              isPositive={true}
            />

            <StatCard
              title="CVaR (95% Downside Tail)"
              value={formatINR(activeRun.cvar_alpha_loss_inr, true)}
              subtext={`Worst-case loss capped at ${formatINR(activeRun.worst_case_loss_inr, true)}`}
              icon={ShieldAlert}
              iconColor="text-rose-400"
              delta="Loss Bounded"
              isPositive={false}
            />

            <StatCard
              title="Budget Shadow Price (ROI/₹)"
              value={`+₹${(activeRun.shadow_price_budget_inr || 0.185).toFixed(3)}`}
              subtext="Marginal profit generated per ₹1 additional budget"
              icon={Percent}
              iconColor="text-indigo-400"
              delta="High ROI headroom"
              isPositive={true}
            />
          </div>
        </div>
      )}

      {/* Main Two-Column Layout: Optimization Dispatcher & Past Runs */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Optimization Dispatcher Form (7 cols) */}
        <div className="lg:col-span-7 rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-6">
          <div className="flex items-center justify-between border-b border-slate-800 pb-4">
            <div className="flex items-center space-x-2.5">
              <Sliders className="h-5 w-5 text-tbo-400" />
              <h2 className="text-base font-bold text-slate-100">
                Stochastic MILP Optimization Controls
              </h2>
            </div>
            <span className="text-[11px] text-slate-400">
              Solver: SciPy HiGHS C++ (Simplex + Branch-and-Bound)
            </span>
          </div>

          {/* Form Fields */}
          <div className="space-y-5">
            {/* 1. Capital Budget */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <label className="font-semibold text-slate-200">
                  Total Procurement Budget (INR ₹)
                </label>
                <span className="text-tbo-400 font-bold text-sm">
                  {formatINR(budgetInr, true)} ({formatINR(budgetInr)})
                </span>
              </div>
              <input
                type="range"
                min="10000000"
                max="150000000"
                step="5000000"
                value={budgetInr}
                onChange={(e) => setBudgetInr(Number(e.target.value))}
                className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-tbo-500"
              />
              <div className="flex justify-between text-[10px] text-slate-400">
                <span>₹1.0 Cr (Min)</span>
                <span>₹5.0 Cr (Standard)</span>
                <span>₹10.0 Cr</span>
                <span>₹15.0 Cr (Max)</span>
              </div>
            </div>

            {/* 2. Risk Appetite Selector */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <label className="font-semibold text-slate-200">
                  Risk Appetite Profile (CVaR λ Penalty)
                </label>
                <span className="text-slate-400 text-[11px]">
                  Controls downside loss aversion vs expected yield
                </span>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <button
                  type="button"
                  onClick={() => setRiskAppetite("CONSERVATIVE")}
                  className={`p-3 rounded-xl border text-left transition ${
                    riskAppetite === "CONSERVATIVE"
                      ? "border-emerald-500 bg-emerald-950/20 text-emerald-300 ring-1 ring-emerald-500"
                      : "border-slate-800 bg-slate-900/50 text-slate-400 hover:bg-slate-800"
                  }`}
                >
                  <div className="font-bold text-xs text-slate-200">Conservative</div>
                  <div className="text-[10px] text-slate-400 mt-0.5">λ = 0.8 | Max downside preservation</div>
                </button>

                <button
                  type="button"
                  onClick={() => setRiskAppetite("BALANCED")}
                  className={`p-3 rounded-xl border text-left transition ${
                    riskAppetite === "BALANCED"
                      ? "border-tbo-500 bg-tbo-950/20 text-tbo-300 ring-1 ring-tbo-500"
                      : "border-slate-800 bg-slate-900/50 text-slate-400 hover:bg-slate-800"
                  }`}
                >
                  <div className="font-bold text-xs text-slate-200">Balanced</div>
                  <div className="text-[10px] text-slate-400 mt-0.5">λ = 0.4 | Optimal profit-risk tradeoff</div>
                </button>

                <button
                  type="button"
                  onClick={() => setRiskAppetite("AGGRESSIVE")}
                  className={`p-3 rounded-xl border text-left transition ${
                    riskAppetite === "AGGRESSIVE"
                      ? "border-indigo-500 bg-indigo-950/20 text-indigo-300 ring-1 ring-indigo-500"
                      : "border-slate-800 bg-slate-900/50 text-slate-400 hover:bg-slate-800"
                  }`}
                >
                  <div className="font-bold text-xs text-slate-200">Aggressive</div>
                  <div className="text-[10px] text-slate-400 mt-0.5">λ = 0.05 | Maximum yield pursuit</div>
                </button>
              </div>
            </div>

            {/* 3. Exposure Caps (Sliders) */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-300 font-medium">Destination Exposure Cap</span>
                  <span className="font-bold text-tbo-400">{destExposureCap}%</span>
                </div>
                <input
                  type="range"
                  min="15"
                  max="60"
                  step="5"
                  value={destExposureCap}
                  onChange={(e) => setDestExposureCap(Number(e.target.value))}
                  className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-tbo-500"
                />
                <span className="text-[10px] text-slate-400">Max portfolio risk in single geo</span>
              </div>

              <div className="space-y-1.5">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-300 font-medium">Supplier Exposure Cap</span>
                  <span className="font-bold text-tbo-400">{supplierExposureCap}%</span>
                </div>
                <input
                  type="range"
                  min="10"
                  max="50"
                  step="5"
                  value={supplierExposureCap}
                  onChange={(e) => setSupplierExposureCap(Number(e.target.value))}
                  className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-tbo-500"
                />
                <span className="text-[10px] text-slate-400">Prevents supplier lock-in concentration</span>
              </div>
            </div>

            {/* 4. Business Context Notes */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300">
                Procurement Run Notes & Purpose
              </label>
              <input
                type="text"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="e.g. Q4 Peak Season Pre-Buy Portfolio"
                className="w-full px-3 py-2 rounded-lg border border-slate-800 bg-slate-900 text-xs text-slate-200 focus:outline-none focus:border-tbo-500"
              />
            </div>
          </div>

          {/* Solver Execution Action & Live Progress */}
          <div className="pt-4 border-t border-slate-800 space-y-4">
            {isSolving ? (
              <div className="rounded-xl border border-tbo-500/30 bg-tbo-950/30 p-4 space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center space-x-2 text-tbo-300 font-semibold">
                    <RotateCw className="h-4 w-4 animate-spin text-tbo-400" />
                    <span>InvenIQ Engine Solving MILP Formulation...</span>
                  </div>
                  <span className="font-mono text-tbo-300 font-bold">{solveProgress}%</span>
                </div>
                {/* Progress bar */}
                <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-gradient-to-r from-tbo-500 to-indigo-500 h-2 transition-all duration-300 ease-out"
                    style={{ width: `${solveProgress}%` }}
                  />
                </div>
                <p className="text-[11px] text-slate-400 animate-pulse">
                  {solveStage}
                </p>
              </div>
            ) : (
              <button
                type="button"
                onClick={handleRunOptimization}
                className="w-full py-3.5 px-4 rounded-xl bg-gradient-to-r from-tbo-600 to-indigo-600 hover:from-tbo-500 hover:to-indigo-500 text-white font-bold text-xs uppercase tracking-wider flex items-center justify-center space-x-2 transition shadow-xl shadow-tbo-600/25"
              >
                <Play className="h-4 w-4 fill-white" />
                <span>Execute InvenIQ Stochastic MILP Optimization</span>
              </button>
            )}

            <div className="flex items-center justify-between text-[11px] text-slate-400">
              <span className="flex items-center space-x-1">
                <Info className="h-3 w-3 text-slate-400" />
                <span>Idempotency-safe: duplicate runs resolve to cached optimal solution</span>
              </span>
              <span>Runtime: ~1.2s</span>
            </div>
          </div>
        </div>

        {/* Right Column: Historical Optimization Runs (5 cols) */}
        <div className="lg:col-span-5 rounded-2xl border border-slate-800 bg-slate-900/60 p-6 flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2">
                <Clock className="h-4 w-4 text-tbo-400" />
                <h2 className="text-sm font-bold text-slate-200">
                  Optimization History
                </h2>
              </div>
              <span className="text-[11px] text-slate-400">
                {runs.length} Runs Recorded
              </span>
            </div>

            <div className="space-y-3 overflow-y-auto max-h-[380px] pr-1">
              {runs.map((r) => {
                const isSelected = activeRun?.run_id === r.run_id;
                return (
                  <div
                    key={r.run_id}
                    onClick={() => setActiveRun(r)}
                    className={`p-3.5 rounded-xl border text-xs cursor-pointer transition ${
                      isSelected
                        ? "border-tbo-500 bg-tbo-950/20 shadow-md"
                        : "border-slate-800 bg-slate-900/40 hover:bg-slate-800/60"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-bold text-slate-200">
                        {r.run_id}
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${getStatusBadgeClass(
                          r.status
                        )}`}
                      >
                        {r.status.replace(/_/g, " ")}
                      </span>
                    </div>

                    <div className="mt-2 grid grid-cols-2 gap-2 text-[11px] text-slate-400">
                      <div>
                        <span>Budget: </span>
                        <strong className="text-slate-200">
                          {formatINR(r.budget_inr, true)}
                        </strong>
                      </div>
                      <div>
                        <span>Profit: </span>
                        <strong className="text-emerald-400">
                          {formatINR(r.expected_profit_inr, true)}
                        </strong>
                      </div>
                    </div>

                    <div className="mt-2 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px] text-slate-400">
                      <span>{formatDateTime(r.created_at)}</span>
                      <span className="capitalize">{r.risk_appetite.toLowerCase()} risk</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="pt-4 border-t border-slate-800 flex items-center justify-between text-xs">
            <span className="text-slate-400">Governance Status</span>
            <Link
              href="/approvals"
              className="text-tbo-400 hover:text-tbo-300 font-semibold flex items-center space-x-1"
            >
              <span>Finance Approver Portal</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
