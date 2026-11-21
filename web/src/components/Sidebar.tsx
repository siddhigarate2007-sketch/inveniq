"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Sparkles,
  PieChart,
  TrendingDown,
  SlidersHorizontal,
  HeartPulse,
  ShieldCheck,
  FileSpreadsheet,
} from "lucide-react";

const NAV_ITEMS = [
  {
    name: "Command Center",
    href: "/",
    icon: LayoutDashboard,
    badge: null,
  },
  {
    name: "Recommendations",
    href: "/recommendations",
    icon: Sparkles,
    badge: "42 Buys",
  },
  {
    name: "Budget Allocation",
    href: "/allocation",
    icon: PieChart,
    badge: null,
  },
  {
    name: "Risk & Scenarios",
    href: "/risk",
    icon: TrendingDown,
    badge: "CVaR 95%",
  },
  {
    name: "What-If Simulator",
    href: "/simulator",
    icon: SlidersHorizontal,
    badge: "Interactive",
  },
  {
    name: "Model Health & Drift",
    href: "/health",
    icon: HeartPulse,
    badge: "14.4% WMAPE",
  },
  {
    name: "Approvals & Audit",
    href: "/approvals",
    icon: ShieldCheck,
    badge: "Finance",
  },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 border-r border-slate-800 bg-navy-950 flex flex-col justify-between shrink-0 hidden lg:flex">
      <div className="py-6 px-4 space-y-1">
        <div className="px-3 pb-3">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            Decision Suite
          </p>
        </div>

        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-medium transition ${
                isActive
                  ? "bg-tbo-600/20 text-tbo-300 border border-tbo-500/30 shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/60"
              }`}
            >
              <div className="flex items-center space-x-3">
                <Icon
                  className={`h-4 w-4 ${
                    isActive ? "text-tbo-400" : "text-slate-400"
                  }`}
                />
                <span>{item.name}</span>
              </div>
              {item.badge && (
                <span
                  className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${
                    isActive
                      ? "bg-tbo-500/30 text-tbo-200"
                      : "bg-slate-800 text-slate-400"
                  }`}
                >
                  {item.badge}
                </span>
              )}
            </Link>
          );
        })}
      </div>

      {/* Footer Info Box */}
      <div className="p-4 m-4 rounded-xl border border-slate-800 bg-slate-900/60">
        <div className="flex items-center space-x-2 text-xs font-semibold text-slate-300 mb-1">
          <FileSpreadsheet className="h-4 w-4 text-tbo-400" />
          <span>Active Procurement Run</span>
        </div>
        <p className="text-[11px] text-slate-400">
          RUN_20261120_001 (Q4 High Season)
        </p>
        <div className="mt-2.5 pt-2 border-t border-slate-800 flex items-center justify-between text-[11px]">
          <span className="text-slate-400">Committed:</span>
          <span className="font-semibold text-emerald-400">₹4.86 Cr</span>
        </div>
      </div>
    </aside>
  );
}
