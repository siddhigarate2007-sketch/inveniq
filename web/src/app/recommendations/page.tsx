"use client";

import React, { useEffect, useState } from "react";
import {
  Search,
  Filter,
  Download,
  Building,
  Plane,
  Sparkles,
  TrendingUp,
  Eye,
  CheckCircle2,
  Clock,
  ChevronRight,
} from "lucide-react";
import DrillDownModal from "@/components/DrillDownModal";
import { api } from "@/lib/api";
import { formatINR, formatPercent } from "@/lib/formatters";
import { Destination, RecommendationItem } from "@/lib/types";

export default function RecommendationsPage() {
  const [items, setItems] = useState<RecommendationItem[]>([]);
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  // Filters & Search
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedDest, setSelectedDest] = useState<string>("ALL");
  const [selectedType, setSelectedType] = useState<string>("ALL");
  const [selectedTiming, setSelectedTiming] = useState<string>("ALL");

  // Drill-down Modal selection
  const [activeItem, setActiveItem] = useState<RecommendationItem | null>(null);

  useEffect(() => {
    loadRecommendations();
  }, []);

  const loadRecommendations = async () => {
    try {
      setLoading(true);
      const runs = await api.listRuns();
      if (runs.length > 0 && runs[0].recommendations) {
        setItems(runs[0].recommendations);
      }
      const dests = await api.getDestinations();
      setDestinations(dests);
    } finally {
      setLoading(false);
    }
  };

  // Filtered List
  const filteredItems = items.filter((item) => {
    const matchesSearch =
      (item.property_name || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
      (item.route_code || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.item_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.supplier_id.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesDest =
      selectedDest === "ALL" || item.destination_id === selectedDest;
    const matchesType =
      selectedType === "ALL" || item.product_type === selectedType;
    const matchesTiming =
      selectedTiming === "ALL" || item.buy_timing_recommendation === selectedTiming;

    return matchesSearch && matchesDest && matchesType && matchesTiming;
  });

  // Aggregated totals
  const totalInvestment = filteredItems.reduce((acc, i) => acc + i.total_investment_inr, 0);
  const totalProfit = filteredItems.reduce((acc, i) => acc + i.expected_profit_inr, 0);
  const avgSellThrough =
    filteredItems.length > 0
      ? filteredItems.reduce((acc, i) => acc + i.sell_through_probability, 0) /
        filteredItems.length
      : 0;

  const handleExportCSV = () => {
    const headers = [
      "Item ID",
      "Property / Route",
      "Product Type",
      "Destination",
      "Supplier",
      "Procure Qty",
      "Allotment",
      "Unit Cost (INR)",
      "Sell Price (INR)",
      "Total Investment (INR)",
      "Expected Profit (INR)",
      "Sell-Through %",
      "Opportunity Score",
      "Buy Timing",
    ];

    const rows = filteredItems.map((i) => [
      i.item_id,
      `"${i.property_name || i.route_code || i.item_id}"`,
      i.product_type,
      i.destination_id,
      i.supplier_id,
      i.procure_quantity,
      i.allotment_available,
      i.unit_cost_inr,
      i.suggested_sell_price_inr,
      i.total_investment_inr,
      i.expected_profit_inr,
      `${(i.sell_through_probability * 100).toFixed(1)}%`,
      i.opportunity_score || "",
      i.buy_timing_recommendation,
    ]);

    const csvContent =
      "data:text/csv;charset=utf-8," +
      [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `InvenIQ_PreBuy_Recommendations_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-slate-100 flex items-center space-x-3">
            <span>Ranked Inventory Buy Recommendations</span>
            <span className="text-xs px-2.5 py-0.5 rounded-full font-bold bg-tbo-500/20 text-tbo-300 border border-tbo-500/30">
              Pareto Optimal
            </span>
          </h1>
          <p className="text-xs md:text-sm text-slate-400 mt-1">
            Prioritized by 5-pillar Opportunity Score, marginal CVaR contribution, and calibrated sell-through probability.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={handleExportCSV}
            className="px-3.5 py-2 rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold flex items-center space-x-2 transition"
          >
            <Download className="h-4 w-4 text-slate-400" />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {/* Aggregate Metrics Header Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 rounded-xl border border-slate-800 bg-slate-900/60">
        <div>
          <span className="text-[11px] text-slate-400">Recommended Blocks</span>
          <p className="text-lg font-bold text-slate-100">
            {filteredItems.length} <span className="text-xs font-normal text-slate-400">units</span>
          </p>
        </div>
        <div>
          <span className="text-[11px] text-slate-400">Total Capital Committed</span>
          <p className="text-lg font-bold text-blue-400">
            {formatINR(totalInvestment, true)}
          </p>
        </div>
        <div>
          <span className="text-[11px] text-slate-400">Expected Net Profit</span>
          <p className="text-lg font-bold text-emerald-400">
            {formatINR(totalProfit, true)}{" "}
            <span className="text-xs font-normal text-slate-400">
              ({totalInvestment > 0 ? ((totalProfit / totalInvestment) * 100).toFixed(1) : "0"}% ROI)
            </span>
          </p>
        </div>
        <div>
          <span className="text-[11px] text-slate-400">Avg. Sell-Through Prob.</span>
          <p className="text-lg font-bold text-indigo-400">
            {(avgSellThrough * 100).toFixed(1)}%
          </p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        {/* Search */}
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search hotels, flight routes, suppliers, item ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 rounded-lg border border-slate-800 bg-slate-900 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-tbo-500"
          />
        </div>

        {/* Dropdown Filters */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Destination Filter */}
          <select
            value={selectedDest}
            onChange={(e) => setSelectedDest(e.target.value)}
            className="px-3 py-2 rounded-lg border border-slate-800 bg-slate-900 text-xs text-slate-300 focus:outline-none focus:border-tbo-500"
          >
            <option value="ALL">All Destinations</option>
            {destinations.map((d) => (
              <option key={d.destination_id} value={d.destination_id}>
                {d.name}
              </option>
            ))}
          </select>

          {/* Product Type Filter */}
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="px-3 py-2 rounded-lg border border-slate-800 bg-slate-900 text-xs text-slate-300 focus:outline-none focus:border-tbo-500"
          >
            <option value="ALL">All Products</option>
            <option value="HOTEL">Hotels</option>
            <option value="FLIGHT">Flights</option>
          </select>

          {/* Buy Timing Filter */}
          <select
            value={selectedTiming}
            onChange={(e) => setSelectedTiming(e.target.value)}
            className="px-3 py-2 rounded-lg border border-slate-800 bg-slate-900 text-xs text-slate-300 focus:outline-none focus:border-tbo-500"
          >
            <option value="ALL">All Timings</option>
            <option value="BUY_NOW">Buy Now</option>
            <option value="WAIT_MONITOR">Wait & Monitor</option>
          </select>
        </div>
      </div>

      {/* Recommendations Table */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950/80 text-[11px] uppercase tracking-wider text-slate-400 border-b border-slate-800 font-semibold">
              <tr>
                <th className="py-3.5 px-4">Score</th>
                <th className="py-3.5 px-4">Inventory Property / Flight</th>
                <th className="py-3.5 px-4">Destination & Supplier</th>
                <th className="py-3.5 px-4 text-right">Pre-Buy Qty</th>
                <th className="py-3.5 px-4 text-right">Unit Cost / Price</th>
                <th className="py-3.5 px-4 text-right">Investment</th>
                <th className="py-3.5 px-4 text-right">Expected Profit</th>
                <th className="py-3.5 px-4 text-center">Timing</th>
                <th className="py-3.5 px-4 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {filteredItems.map((item, idx) => {
                const marginPct = Math.round(
                  ((item.suggested_sell_price_inr - item.unit_cost_inr) /
                    item.unit_cost_inr) *
                    100
                );

                return (
                  <tr
                    key={item.item_id}
                    className="hover:bg-slate-800/50 transition cursor-pointer group"
                    onClick={() => setActiveItem(item)}
                  >
                    {/* Opportunity Score */}
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <div className="flex items-center space-x-1.5">
                        <span className="font-mono font-bold text-xs px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                          {item.opportunity_score?.toFixed(1) || "88.5"}
                        </span>
                      </div>
                    </td>

                    {/* Property / Flight Title */}
                    <td className="py-3.5 px-4">
                      <div className="flex items-start space-x-2.5">
                        <div
                          className={`mt-0.5 p-1 rounded ${
                            item.product_type === "HOTEL"
                              ? "bg-amber-500/10 text-amber-400"
                              : "bg-blue-500/10 text-blue-400"
                          }`}
                        >
                          {item.product_type === "HOTEL" ? (
                            <Building className="h-3.5 w-3.5" />
                          ) : (
                            <Plane className="h-3.5 w-3.5" />
                          )}
                        </div>
                        <div>
                          <p className="font-semibold text-slate-100 group-hover:text-tbo-400 transition">
                            {item.property_name || item.route_code || item.item_id}
                          </p>
                          <p className="text-[10px] text-slate-400 line-clamp-1 max-w-xs mt-0.5">
                            {item.reason_string}
                          </p>
                        </div>
                      </div>
                    </td>

                    {/* Destination & Supplier */}
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <p className="font-medium text-slate-200">
                        {item.destination_id.replace("DEST_", "")}
                      </p>
                      <p className="text-[10px] text-slate-400">{item.supplier_id}</p>
                    </td>

                    {/* Quantity / Allotment */}
                    <td className="py-3.5 px-4 text-right whitespace-nowrap">
                      <p className="font-bold text-slate-100">
                        {item.procure_quantity}{" "}
                        <span className="text-[10px] font-normal text-slate-400">
                          / {item.allotment_available}
                        </span>
                      </p>
                      <p className="text-[10px] text-slate-400">
                        MOQ: {item.min_order_qty}
                      </p>
                    </td>

                    {/* Pricing & Margin */}
                    <td className="py-3.5 px-4 text-right whitespace-nowrap">
                      <p className="font-bold text-emerald-400">
                        {formatINR(item.suggested_sell_price_inr)}
                      </p>
                      <p className="text-[10px] text-slate-400">
                        Cost: {formatINR(item.unit_cost_inr)} (+{marginPct}%)
                      </p>
                    </td>

                    {/* Total Investment */}
                    <td className="py-3.5 px-4 text-right whitespace-nowrap">
                      <p className="font-semibold text-slate-200">
                        {formatINR(item.total_investment_inr, true)}
                      </p>
                    </td>

                    {/* Expected Profit & Probability */}
                    <td className="py-3.5 px-4 text-right whitespace-nowrap">
                      <p className="font-bold text-emerald-400">
                        {formatINR(item.expected_profit_inr, true)}
                      </p>
                      <p className="text-[10px] text-indigo-300">
                        {(item.sell_through_probability * 100).toFixed(0)}% sell-thru
                      </p>
                    </td>

                    {/* Timing Badge */}
                    <td className="py-3.5 px-4 text-center whitespace-nowrap">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                        {item.buy_timing_recommendation}
                      </span>
                    </td>

                    {/* Action */}
                    <td className="py-3.5 px-4 text-center whitespace-nowrap">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setActiveItem(item);
                        }}
                        className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-tbo-400 text-[11px] font-semibold flex items-center space-x-1 mx-auto transition"
                      >
                        <Eye className="h-3.5 w-3.5" />
                        <span>Inspect</span>
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Drill Down Modal */}
      <DrillDownModal item={activeItem} onClose={() => setActiveItem(null)} />
    </div>
  );
}
