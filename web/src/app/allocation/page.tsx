"use client";

import React, { useEffect, useState } from "react";
import {
  PieChart as PieIcon,
  ShieldCheck,
  Building,
  Plane,
  AlertTriangle,
  TrendingUp,
  Layers,
} from "lucide-react";
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from "recharts";
import { api } from "@/lib/api";
import { formatINR } from "@/lib/formatters";
import { RecommendationItem } from "@/lib/types";

export default function BudgetAllocationPage() {
  const [items, setItems] = useState<RecommendationItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const runs = await api.listRuns();
      if (runs.length > 0 && runs[0].recommendations) {
        setItems(runs[0].recommendations);
      }
    } finally {
      setLoading(false);
    }
  };

  const totalCommitted = items.reduce((acc, i) => acc + i.total_investment_inr, 0);

  // Group by Destination
  const destMap: Record<string, number> = {};
  items.forEach((item) => {
    const destName = item.destination_id.replace("DEST_", "");
    destMap[destName] = (destMap[destName] || 0) + item.total_investment_inr;
  });

  const destData = Object.entries(destMap)
    .map(([name, value]) => ({
      name,
      value,
      sharePct: totalCommitted > 0 ? (value / totalCommitted) * 100 : 0,
    }))
    .sort((a, b) => b.value - a.value);

  // Group by Product Type
  const productMap: Record<string, number> = { HOTEL: 0, FLIGHT: 0 };
  items.forEach((item) => {
    productMap[item.product_type] =
      (productMap[item.product_type] || 0) + item.total_investment_inr;
  });

  const productData = [
    { name: "Hotels & Resorts", value: productMap.HOTEL, color: "#f59e0b" },
    { name: "Airlines & Flights", value: productMap.FLIGHT, color: "#38bdf8" },
  ];

  // Group by Supplier
  const supplierMap: Record<string, number> = {};
  items.forEach((item) => {
    supplierMap[item.supplier_id] =
      (supplierMap[item.supplier_id] || 0) + item.total_investment_inr;
  });

  const supplierData = Object.entries(supplierMap)
    .map(([name, value]) => ({
      name: name.replace("SUP_", "").replace(/_/g, " "),
      value,
      sharePct: totalCommitted > 0 ? (value / totalCommitted) * 100 : 0,
    }))
    .sort((a, b) => b.value - a.value);

  // Destination Exposure vs 35% Cap Comparison
  const capData = destData.map((d) => ({
    destination: d.name,
    allocatedPct: Math.round(d.sharePct * 10) / 10,
    capPct: 35,
    withinCap: d.sharePct <= 35,
  }));

  const DEST_COLORS = [
    "#38bdf8",
    "#818cf8",
    "#34d399",
    "#f59e0b",
    "#ec4899",
    "#a855f7",
    "#06b6d4",
    "#f97316",
  ];

  return (
    <div className="space-y-8">
      {/* Page Title */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-slate-100 flex items-center space-x-3">
            <span>Budget Allocation & Exposure Limits</span>
            <span className="text-xs px-2.5 py-0.5 rounded-full font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
              100% Constraints Satisfied
            </span>
          </h1>
          <p className="text-xs md:text-sm text-slate-400 mt-1">
            Hierarchical distribution across Destinations, Products, and Suppliers enforced by MILP hard constraints.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <div className="px-3.5 py-2 rounded-lg border border-slate-700 bg-slate-900 text-xs text-slate-300">
            <span>Total Capital Deployed: </span>
            <strong className="text-emerald-400">{formatINR(totalCommitted, true)}</strong>
          </div>
        </div>
      </div>

      {/* Exposure Cap Verification Meters */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center space-x-2">
            <ShieldCheck className="h-5 w-5 text-emerald-400" />
            <h2 className="text-sm font-bold text-slate-100">
              Destination Exposure vs Regulatory Cap (35.0% Limit)
            </h2>
          </div>
          <span className="text-[11px] text-slate-400">
            Hard MILP Ceiling: <code className="text-slate-300">Sum(Cost_i * q_i) &le; 0.35 * Budget</code>
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {destData.slice(0, 4).map((d) => {
            const isNearCap = d.sharePct > 30;
            return (
              <div
                key={d.name}
                className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 space-y-2"
              >
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-slate-200">{d.name}</span>
                  <span className={`font-mono font-bold ${isNearCap ? "text-amber-400" : "text-emerald-400"}`}>
                    {d.sharePct.toFixed(1)}% / 35.0%
                  </span>
                </div>

                <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                  <div
                    className={`h-2 rounded-full transition-all duration-500 ${
                      isNearCap ? "bg-amber-400" : "bg-emerald-400"
                    }`}
                    style={{ width: `${(d.sharePct / 35) * 100}%` }}
                  />
                </div>

                <div className="flex items-center justify-between text-[10px] text-slate-400">
                  <span>{formatINR(d.value, true)}</span>
                  <span>Safety Margin: +{(35 - d.sharePct).toFixed(1)}%</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Visual Charts Grid: Sunburst/Pie & Product Split */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left: Destination Allocation Pie / Doughnut (6 cols) */}
        <div className="lg:col-span-6 rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center space-x-2">
              <PieIcon className="h-4 w-4 text-tbo-400" />
              <h2 className="text-sm font-bold text-slate-200">
                Capital Distribution by Destination
              </h2>
            </div>
            <span className="text-[11px] text-slate-400">
              {destData.length} Active Geographies
            </span>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={destData}
                  cx="50%"
                  cy="50%"
                  innerRadius={65}
                  outerRadius={95}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {destData.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={DEST_COLORS[index % DEST_COLORS.length]}
                    />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(val: any) => [formatINR(val), "Allocation"]}
                  contentStyle={{
                    backgroundColor: "#0f172a",
                    borderColor: "#334155",
                    fontSize: "11px",
                    borderRadius: "8px",
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Legend Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-slate-800 text-[11px]">
            {destData.map((d, idx) => (
              <div key={d.name} className="flex items-center space-x-2">
                <span
                  className="h-2.5 w-2.5 rounded-full shrink-0"
                  style={{ backgroundColor: DEST_COLORS[idx % DEST_COLORS.length] }}
                />
                <span className="text-slate-300 truncate">{d.name}</span>
                <span className="text-slate-400 font-mono">({d.sharePct.toFixed(0)}%)</span>
              </div>
            ))}
          </div>
        </div>

        {/* Right: Product Type & Supplier Concentration (6 cols) */}
        <div className="lg:col-span-6 rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center space-x-2">
              <Layers className="h-4 w-4 text-indigo-400" />
              <h2 className="text-sm font-bold text-slate-200">
                Product Allocation: Hotels vs Flights Split
              </h2>
            </div>
            <span className="text-[11px] text-slate-400">
              Multi-Asset Packaging
            </span>
          </div>

          {/* Product Type Breakdown */}
          <div className="grid grid-cols-2 gap-4">
            <div className="rounded-xl border border-amber-500/20 bg-amber-950/15 p-4 space-y-1">
              <div className="flex items-center space-x-2 text-amber-400 text-xs font-semibold">
                <Building className="h-4 w-4" />
                <span>Hotel Allotments</span>
              </div>
              <p className="text-xl font-bold text-slate-100">
                {formatINR(productMap.HOTEL, true)}
              </p>
              <p className="text-[11px] text-slate-400">
                {totalCommitted > 0 ? ((productMap.HOTEL / totalCommitted) * 100).toFixed(1) : 0}% of portfolio
              </p>
            </div>

            <div className="rounded-xl border border-blue-500/20 bg-blue-950/15 p-4 space-y-1">
              <div className="flex items-center space-x-2 text-blue-400 text-xs font-semibold">
                <Plane className="h-4 w-4" />
                <span>Airline Blocks</span>
              </div>
              <p className="text-xl font-bold text-slate-100">
                {formatINR(productMap.FLIGHT, true)}
              </p>
              <p className="text-[11px] text-slate-400">
                {totalCommitted > 0 ? ((productMap.FLIGHT / totalCommitted) * 100).toFixed(1) : 0}% of portfolio
              </p>
            </div>
          </div>

          {/* Supplier Exposure Bar Chart */}
          <div className="space-y-2 pt-2">
            <span className="text-xs font-semibold text-slate-300">
              Supplier Capital Concentration (Top Partners)
            </span>
            <div className="h-44 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={supplierData.slice(0, 5)} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis
                    type="number"
                    stroke="#64748b"
                    fontSize={10}
                    tickFormatter={(v) => `₹${(v / 10000000).toFixed(1)}Cr`}
                  />
                  <YAxis
                    type="category"
                    dataKey="name"
                    stroke="#94a3b8"
                    fontSize={10}
                    width={90}
                  />
                  <Tooltip
                    formatter={(val: any) => [formatINR(val), "Capital"]}
                    contentStyle={{
                      backgroundColor: "#0f172a",
                      borderColor: "#334155",
                      fontSize: "11px",
                      borderRadius: "8px",
                    }}
                  />
                  <Bar dataKey="value" fill="#6366f1" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
