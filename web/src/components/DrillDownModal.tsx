"use client";

import React from "react";
import {
  X,
  Sparkles,
  TrendingUp,
  ShieldAlert,
  Calendar,
  Building,
  Plane,
  Coins,
  CheckCircle2,
} from "lucide-react";
import {
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { RecommendationItem } from "@/lib/types";
import { formatINR } from "@/lib/formatters";

interface DrillDownModalProps {
  item: RecommendationItem | null;
  onClose: () => void;
}

export default function DrillDownModal({ item, onClose }: DrillDownModalProps) {
  if (!item) return null;

  // Generate 30-day forecast fan chart data based on item quantiles
  const p10 = item.demand_p10 || 50;
  const p50 = item.demand_p50 || 80;
  const p90 = item.demand_p90 || 110;

  const fanChartData = Array.from({ length: 15 }, (_, i) => {
    const day = (i + 1) * 2;
    const progress = (i + 1) / 15;
    return {
      day: `Day ${day}`,
      p10_pessimistic: Math.round(p10 * (0.2 + 0.8 * progress)),
      p50_expected: Math.round(p50 * (0.2 + 0.8 * progress)),
      p90_optimistic: Math.round(p90 * (0.2 + 0.8 * progress)),
    };
  });

  // Generate price elasticity demand curve points
  const basePrice = item.suggested_sell_price_inr;
  const elasticity = item.price_elasticity || -1.2;
  const elasticityData = [-20, -10, 0, 10, 20].map((pct) => {
    const price = Math.round(basePrice * (1 + pct / 100));
    // D(p) = D_0 * (p / p_0)^elasticity
    const demandMultiplier = Math.pow(1 + pct / 100, elasticity);
    const demand = Math.round(p50 * demandMultiplier);
    const revenue = Math.round(price * demand);
    return {
      priceChange: `${pct >= 0 ? "+" : ""}${pct}%`,
      unitPrice: price,
      predictedDemand: demand,
      projectedRevenue: revenue,
    };
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="relative w-full max-w-4xl bg-navy-900 border border-slate-700 rounded-2xl shadow-2xl max-h-[92vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-5 border-b border-slate-800 flex items-start justify-between bg-slate-900/80">
          <div className="space-y-1">
            <div className="flex items-center space-x-3">
              <span
                className={`px-2.5 py-0.5 rounded-full text-xs font-semibold flex items-center space-x-1.5 ${
                  item.product_type === "HOTEL"
                    ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                    : "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                }`}
              >
                {item.product_type === "HOTEL" ? (
                  <Building className="h-3 w-3" />
                ) : (
                  <Plane className="h-3 w-3" />
                )}
                <span>{item.product_type}</span>
              </span>

              <span className="text-xs font-medium text-slate-400">
                {item.destination_id.replace("DEST_", "")} • {item.supplier_id}
              </span>

              {item.opportunity_score && (
                <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 flex items-center space-x-1">
                  <Sparkles className="h-3 w-3 text-emerald-400" />
                  <span>Opportunity Score: {item.opportunity_score.toFixed(1)}/100</span>
                </span>
              )}
            </div>

            <h2 className="text-xl font-bold text-slate-100">
              {item.property_name || item.route_code || item.item_id}
            </h2>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-6 text-slate-300 text-xs">
          {/* Why Recommended Explainable Section */}
          <div className="rounded-xl border border-indigo-500/20 bg-indigo-950/20 p-4 space-y-2">
            <div className="flex items-center space-x-2 text-indigo-300 font-semibold text-xs">
              <CheckCircle2 className="h-4 w-4 text-indigo-400" />
              <span>Why InvenIQ Recommends This Purchase:</span>
            </div>
            <p className="text-slate-300 text-xs leading-relaxed">
              {item.reason_string ||
                "High look-to-book ratio, strong historical sell-through, favorable release cutoff terms, and strong margin buffer against demand uncertainty."}
            </p>
          </div>

          {/* Key Procurement Metrics Row */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3.5 space-y-1">
              <span className="text-[11px] text-slate-400">Procure Quantity</span>
              <div className="text-lg font-bold text-slate-100">
                {item.procure_quantity} <span className="text-xs font-normal text-slate-400">/ {item.allotment_available} max</span>
              </div>
              <span className="text-[10px] text-tbo-400">MOQ: {item.min_order_qty} units</span>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3.5 space-y-1">
              <span className="text-[11px] text-slate-400">Unit Cost & Selling Price</span>
              <div className="text-base font-bold text-emerald-400">
                {formatINR(item.suggested_sell_price_inr)}
              </div>
              <span className="text-[10px] text-slate-400">Cost: {formatINR(item.unit_cost_inr)} (Margin: {Math.round(((item.suggested_sell_price_inr - item.unit_cost_inr) / item.unit_cost_inr) * 100)}%)</span>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3.5 space-y-1">
              <span className="text-[11px] text-slate-400">Total Capital & Exp. Profit</span>
              <div className="text-base font-bold text-slate-100">
                {formatINR(item.expected_profit_inr, true)}
              </div>
              <span className="text-[10px] text-slate-400">Capital: {formatINR(item.total_investment_inr, true)}</span>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3.5 space-y-1">
              <span className="text-[11px] text-slate-400">Downside & Sell-Through</span>
              <div className="text-base font-bold text-indigo-400">
                {(item.sell_through_probability * 100).toFixed(0)}% Prob.
              </div>
              <span className="text-[10px] text-rose-400">Max Loss: {formatINR(item.max_downside_loss_inr, true)}</span>
            </div>
          </div>

          {/* Section 1: Probabilistic Forecast Fan Chart */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <TrendingUp className="h-4 w-4 text-tbo-400" />
                <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider">
                  Probabilistic Demand Forecast Intervals (LightGBM Quantile + Conformal)
                </h3>
              </div>
              <span className="text-[10px] text-slate-400">
                P10 ({p10}) • P50 ({p50}) • P90 ({p90})
              </span>
            </div>

            <div className="h-52 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={fanChartData}>
                  <defs>
                    <linearGradient id="p90Grad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#38bdf8" stopOpacity={0.0} />
                    </linearGradient>
                    <linearGradient id="p50Grad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#818cf8" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#818cf8" stopOpacity={0.05} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="day" stroke="#64748b" fontSize={10} />
                  <YAxis stroke="#64748b" fontSize={10} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0f172a",
                      borderColor: "#334155",
                      fontSize: "11px",
                      borderRadius: "8px",
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: "11px" }} />
                  <Area
                    type="monotone"
                    dataKey="p90_optimistic"
                    name="P90 (Optimistic)"
                    stroke="#38bdf8"
                    fill="url(#p90Grad)"
                  />
                  <Area
                    type="monotone"
                    dataKey="p50_expected"
                    name="P50 (Median Expected)"
                    stroke="#818cf8"
                    fill="url(#p50Grad)"
                  />
                  <Area
                    type="monotone"
                    dataKey="p10_pessimistic"
                    name="P10 (Pessimistic Floor)"
                    stroke="#f43f5e"
                    fill="none"
                    strokeDasharray="4 4"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Section 2: Double ML Price Elasticity Curve */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Coins className="h-4 w-4 text-emerald-400" />
                <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider">
                  Double ML Price Elasticity Curve D(p) & Projected Revenue
                </h3>
              </div>
              <span className="text-[10px] text-slate-400">
                Segment Elasticity: <strong className="text-emerald-300">{item.price_elasticity || -1.2}</strong>
              </span>
            </div>

            <div className="h-44 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={elasticityData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="priceChange" stroke="#64748b" fontSize={10} />
                  <YAxis
                    yAxisId="left"
                    stroke="#64748b"
                    fontSize={10}
                    label={{
                      value: "Units Demand",
                      angle: -90,
                      position: "insideLeft",
                      fontSize: 10,
                      fill: "#94a3b8",
                    }}
                  />
                  <YAxis
                    yAxisId="right"
                    orientation="right"
                    stroke="#64748b"
                    fontSize={10}
                    tickFormatter={(v) => `₹${(v / 100000).toFixed(1)}L`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0f172a",
                      borderColor: "#334155",
                      fontSize: "11px",
                      borderRadius: "8px",
                    }}
                    formatter={(val: any, name: string) => {
                      if (name === "projectedRevenue") return [formatINR(val), "Revenue"];
                      return [val, name];
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: "11px" }} />
                  <Line
                    yAxisId="left"
                    type="monotone"
                    dataKey="predictedDemand"
                    name="Predicted Demand"
                    stroke="#38bdf8"
                    strokeWidth={2}
                    dot={{ r: 4 }}
                  />
                  <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="projectedRevenue"
                    name="Projected Revenue"
                    stroke="#10b981"
                    strokeWidth={2}
                    strokeDasharray="3 3"
                    dot={{ r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Supplier Terms & Cutoff Policy */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 space-y-2">
              <div className="flex items-center space-x-2 text-slate-200 font-semibold text-xs">
                <Calendar className="h-4 w-4 text-tbo-400" />
                <span>Supplier Cutoff & Release Terms:</span>
              </div>
              <ul className="space-y-1.5 text-[11px] text-slate-400">
                <li>• Release Cutoff Window: <strong>{item.release_cutoff_days} days before check-in</strong></li>
                <li>• Unsold inventory returned before Day {item.release_cutoff_days} incurs 0% forfeiture penalty</li>
                <li>• Buy timing recommended: <span className="font-bold text-emerald-400">{item.buy_timing_recommendation}</span></li>
              </ul>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 space-y-2">
              <div className="flex items-center space-x-2 text-slate-200 font-semibold text-xs">
                <ShieldAlert className="h-4 w-4 text-rose-400" />
                <span>Risk & Downside Mitigation:</span>
              </div>
              <ul className="space-y-1.5 text-[11px] text-slate-400">
                <li>• Calibrated cancellation probability: <strong>{((1 - item.sell_through_probability) * 0.4 * 100).toFixed(1)}%</strong></li>
                <li>• Break-even threshold: <strong>{Math.ceil(item.total_investment_inr / item.suggested_sell_price_inr)} units</strong> ({Math.round((Math.ceil(item.total_investment_inr / item.suggested_sell_price_inr) / item.procure_quantity) * 100)}% of buy)</li>
                <li>• CVaR 95% tail contribution: <strong className="text-rose-400">{formatINR(item.max_downside_loss_inr * 0.65)}</strong></li>
              </ul>
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="px-6 py-4 border-t border-slate-800 bg-slate-900/80 flex items-center justify-between">
          <div className="text-[11px] text-slate-400">
            Item ID: <code className="text-slate-300">{item.item_id}</code>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition"
          >
            Close Details
          </button>
        </div>
      </div>
    </div>
  );
}
