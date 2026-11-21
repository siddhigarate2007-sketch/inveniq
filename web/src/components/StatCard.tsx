import React from "react";
import { LucideIcon } from "lucide-react";

interface StatCardProps {
  title: string;
  value: string;
  subtext?: string;
  icon: LucideIcon;
  iconColor?: string;
  delta?: string;
  isPositive?: boolean;
}

export default function StatCard({
  title,
  value,
  subtext,
  icon: Icon,
  iconColor = "text-tbo-400",
  delta,
  isPositive,
}: StatCardProps) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 shadow-sm hover:border-slate-700 transition">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium text-slate-400">{title}</p>
        <div className={`p-2 rounded-lg bg-slate-800/80 ${iconColor}`}>
          <Icon className="h-4 w-4" />
        </div>
      </div>

      <div className="mt-3 flex items-baseline space-x-2">
        <p className="text-2xl font-bold tracking-tight text-slate-100">
          {value}
        </p>
        {delta && (
          <span
            className={`text-xs font-semibold px-1.5 py-0.5 rounded ${
              isPositive
                ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
            }`}
          >
            {delta}
          </span>
        )}
      </div>

      {subtext && (
        <p className="mt-1.5 text-xs text-slate-400 flex items-center space-x-1">
          {subtext}
        </p>
      )}
    </div>
  );
}
