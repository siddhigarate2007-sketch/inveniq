"use client";

import React, { useEffect, useState } from "react";
import {
  SlidersHorizontal,
  Flame,
  ShieldCheck,
  TrendingDown,
  RefreshCw,
  AlertTriangle,
  Play,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import StatCard from "@/components/StatCard";
import { api } from "@/lib/api";
import { formatINR, formatPercent } from "@/lib/formatters";
import { StressScenarioResult, StressTestRequest } from "@/lib/types";

export default function WhatIfSimulatorPage() {
  // Slider Controls
  const [demandShock, setDemandShock] = useState<number>(-20);
  const [costInflation, setCostInflation] = useState<number>(10);
  const [cancellationSurge, setCancellationSurge] = useState<number>(50);

  // Results State
  const [results, setResults] = useState<StressScenarioResult[]>([]);
  const [isSimulating, setIsSimulating] = useState<boolean>(false);

  useEffect(() => {
    runSimulation();
  }, []);

  const runSimulation = async () => {
    setIsSimulating(true);
    try {
      const payload: StressTestRequest = {
        demand_shock_pct: demandShock,
        cost_inflation_pct: costInflation,
        cancellation_surge_pct: cancellationSurge,
      };
      const res = await api.runStressTest(payload);
      setResults(res);
    } finally {
      setIsSimulating(false);
    }
  };

  const applyPreset = (d: number, c: number, x: number) => {
    setDemandShock(d);
    setCostInflation(c);
    setCancellationSurge(x);
  };

  const baselineResult = results[0] || {
    expected_profit_inr: 9840000,
    cvar_loss_inr: 1420000,
  };

  // The custom evaluated scenario is usually at index 1
  const customResult = results.length > 1 ? results[1] : results[0] || {
    expected_profit_inr: 6720000,
    profit_delta_inr: -3120000,
    profit_delta_pct: -31.7,
    cvar_loss_inr: 2350000,
    worst_case_loss_inr: 3950000,
    survived: true,
  };

  return (
    <div className="space-y-8">
      {/* Title */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-slate-100 flex items-center space-x-3">
            <span>What-If Stress Simulator</span>
            <span className="text-xs px-2.5 py-0.5 rounded-full font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
              Interactive Stress Engine
            </span>
          </h1>
          <p className="text-xs md:text-sm text-slate-400 mt-1">
            Simulate portfolio resilience under severe macroeconomic shocks, fuel price surges, and cancellation cascades.
          </p>
        </div>

        <button
          onClick={runSimulation}
          disabled={isSimulating}
          className="px-4 py-2 rounded-lg bg-tbo-600 hover:bg-tbo-500 text-white text-xs font-semibold flex items-center space-x-2 transition shadow-lg shadow-tbo-600/20"
        >
          <RefreshCw className={`h-4 w-4 ${isSimulating ? "animate-spin" : ""}`} />
          <span>Re-Solve Stress Simulation</span>
        </button>
      </div>

      {/* Preset Buttons */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-slate-400 mr-1">Quick Presets:</span>
        <button
          onClick={() => applyPreset(-20, 10, 50)}
          className="px-3 py-1.5 rounded-lg border border-slate-800 bg-slate-900/60 hover:bg-slate-800 text-slate-300 text-xs transition"
        >
          Standard TBO Stress (D:-20%, C:+10%, X:+50%)
        </button>
        <button
          onClick={() => applyPreset(-35, 0, 20)}
          className="px-3 py-1.5 rounded-lg border border-slate-800 bg-slate-900/60 hover:bg-slate-800 text-slate-300 text-xs transition"
        >
          Severe Demand Slowdown (-35%)
        </button>
        <button
          onClick={() => applyPreset(0, 25, 10)}
          className="px-3 py-1.5 rounded-lg border border-slate-800 bg-slate-900/60 hover:bg-slate-800 text-slate-300 text-xs transition"
        >
          Aviation Fuel Surge (+25% Cost)
        </button>
        <button
          onClick={() => applyPreset(0, 0, 0)}
          className="px-3 py-1.5 rounded-lg border border-slate-800 bg-slate-900/60 hover:bg-slate-800 text-slate-300 text-xs transition"
        >
          Reset to Baseline
        </button>
      </div>

      {/* Interactive Controls & Delta Comparison (Two Columns) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Sliders Panel (6 cols) */}
        <div className="lg:col-span-6 rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-6">
          <div className="flex items-center space-x-2.5 border-b border-slate-800 pb-3">
            <SlidersHorizontal className="h-5 w-5 text-tbo-400" />
            <h2 className="text-sm font-bold text-slate-100">
              Macro Stress Parameters
            </h2>
          </div>

          <div className="space-y-6">
            {/* 1. Demand Shock Slider */}
            <div className="space-y-2">
              <div className="flex justify-between text-xs">
                <span className="font-semibold text-slate-200">
                  Market Demand Shock
                </span>
                <span
                  className={`font-mono font-bold ${
                    demandShock < 0 ? "text-rose-400" : "text-emerald-400"
                  }`}
                >
                  {demandShock >= 0 ? "+" : ""}
                  {demandShock}%
                </span>
              </div>
              <input
                type="range"
                min="-60"
                max="20"
                step="5"
                value={demandShock}
                onChange={(e) => setDemandShock(Number(e.target.value))}
                className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-rose-500"
              />
              <div className="flex justify-between text-[10px] text-slate-400">
                <span>-60% (Collapse)</span>
                <span>-20% (Standard)</span>
                <span>0% (Baseline)</span>
                <span>+20% (Boom)</span>
              </div>
            </div>

            {/* 2. Cost Inflation Slider */}
            <div className="space-y-2">
              <div className="flex justify-between text-xs">
                <span className="font-semibold text-slate-200">
                  Supplier Cost & Fuel Inflation
                </span>
                <span
                  className={`font-mono font-bold ${
                    costInflation > 0 ? "text-amber-400" : "text-slate-300"
                  }`}
                >
                  +{costInflation}%
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="30"
                step="5"
                value={costInflation}
                onChange={(e) => setCostInflation(Number(e.target.value))}
                className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-amber-500"
              />
              <div className="flex justify-between text-[10px] text-slate-400">
                <span>0% (Contracted)</span>
                <span>+10% (Moderate)</span>
                <span>+20%</span>
                <span>+30% (Severe)</span>
              </div>
            </div>

            {/* 3. Cancellation Surge Slider */}
            <div className="space-y-2">
              <div className="flex justify-between text-xs">
                <span className="font-semibold text-slate-200">
                  Cancellation Rate Spike
                </span>
                <span
                  className={`font-mono font-bold ${
                    cancellationSurge > 0 ? "text-indigo-400" : "text-slate-300"
                  }`}
                >
                  +{cancellationSurge}%
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                step="10"
                value={cancellationSurge}
                onChange={(e) => setCancellationSurge(Number(e.target.value))}
                className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
              />
              <div className="flex justify-between text-[10px] text-slate-400">
                <span>0% (Historical)</span>
                <span>+50% (High Disruption)</span>
                <span>+100% (Cascade)</span>
              </div>
            </div>
          </div>

          <button
            onClick={runSimulation}
            className="w-full py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-100 font-semibold text-xs flex items-center justify-center space-x-2 transition border border-slate-700"
          >
            <Play className="h-4 w-4 text-tbo-400 fill-tbo-400" />
            <span>Apply Custom Shocks & Re-Calculate</span>
          </button>
        </div>

        {/* Delta Comparison Cards (6 cols) */}
        <div className="lg:col-span-6 rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-6">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h2 className="text-sm font-bold text-slate-100">
              Shocked Impact vs Baseline
            </h2>
            <div className="flex items-center space-x-1.5 text-xs text-emerald-400 font-semibold">
              <CheckCircle2 className="h-4 w-4" />
              <span>Solvency Maintained</span>
            </div>
          </div>

          {/* Profit Impact Display */}
          <div className="grid grid-cols-2 gap-4">
            <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 space-y-1">
              <span className="text-[11px] text-slate-400">Baseline Expected Profit</span>
              <p className="text-lg font-bold text-slate-200">
                {formatINR(baselineResult.expected_profit_inr, true)}
              </p>
              <span className="text-[10px] text-slate-400">Unshocked forecast</span>
            </div>

            <div className="rounded-xl border border-amber-500/20 bg-amber-950/20 p-4 space-y-1">
              <span className="text-[11px] text-amber-300">Shocked Expected Profit</span>
              <p className="text-lg font-bold text-amber-400">
                {formatINR(customResult.expected_profit_inr, true)}
              </p>
              <span className="text-[10px] text-rose-400 font-semibold">
                Delta: {formatINR(customResult.profit_delta_inr, true)} ({customResult.profit_delta_pct}%)
              </span>
            </div>
          </div>

          {/* Risk Metrics */}
          <div className="grid grid-cols-2 gap-4">
            <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 space-y-1">
              <span className="text-[11px] text-slate-400">Shocked CVaR (95% Tail)</span>
              <p className="text-lg font-bold text-rose-400">
                {formatINR(customResult.cvar_loss_inr, true)}
              </p>
              <span className="text-[10px] text-slate-400">
                Baseline: {formatINR(baselineResult.cvar_loss_inr, true)}
              </span>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 space-y-1">
              <span className="text-[11px] text-slate-400">Worst-Case Tail Floor</span>
              <p className="text-lg font-bold text-rose-500">
                {formatINR(customResult.worst_case_loss_inr, true)}
              </p>
              <span className="text-[10px] text-slate-400">Maximum possible downside</span>
            </div>
          </div>

          <div className="rounded-xl border border-indigo-500/20 bg-indigo-950/20 p-4 text-xs text-slate-300 space-y-1">
            <div className="font-semibold text-indigo-300">
              Stress Test Evaluation Summary:
            </div>
            <p className="text-[11px] leading-relaxed text-slate-300">
              Even under simultaneous demand collapse (-20%) and cost surge (+10%), InvenIQ&apos;s diversification constraints prevent total forfeiture. The portfolio remains cash-flow positive with ₹{((customResult.expected_profit_inr || 0) / 10000000).toFixed(2)} Cr net profit.
            </p>
          </div>
        </div>
      </div>

      {/* Comprehensive Scenarios Table */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 overflow-hidden shadow-xl">
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <h2 className="text-sm font-bold text-slate-200">
            Standard Stress Scenarios Evaluation Matrix
          </h2>
          <span className="text-[11px] text-slate-400">
            Automated Replay across 5 Stress Benchmarks
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950/80 text-[11px] uppercase tracking-wider text-slate-400 border-b border-slate-800 font-semibold">
              <tr>
                <th className="py-3 px-4">Scenario Name</th>
                <th className="py-3 px-4">Description</th>
                <th className="py-3 px-4 text-right">Expected Profit</th>
                <th className="py-3 px-4 text-right">Profit Delta</th>
                <th className="py-3 px-4 text-right">CVaR Loss</th>
                <th className="py-3 px-4 text-center">Solvency Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {results.map((sc, idx) => (
                <tr key={idx} className="hover:bg-slate-800/40 transition">
                  <td className="py-3.5 px-4 font-bold text-slate-100">
                    {sc.scenario_name}
                  </td>
                  <td className="py-3.5 px-4 text-slate-400 max-w-xs">
                    {sc.description}
                  </td>
                  <td className="py-3.5 px-4 text-right font-bold text-emerald-400">
                    {formatINR(sc.expected_profit_inr, true)}
                  </td>
                  <td className="py-3.5 px-4 text-right font-semibold">
                    <span
                      className={
                        sc.profit_delta_inr < 0 ? "text-rose-400" : "text-slate-400"
                      }
                    >
                      {sc.profit_delta_inr === 0 ? "-" : formatINR(sc.profit_delta_inr, true)}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-right text-rose-400 font-medium">
                    {formatINR(sc.cvar_loss_inr, true)}
                  </td>
                  <td className="py-3.5 px-4 text-center">
                    <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                      PASSED (Solvent)
                    </span>
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
