"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  ShieldCheck,
  UserCheck,
  Activity,
  Layers,
  ChevronDown,
} from "lucide-react";
import { api } from "@/lib/api";
import { User, UserRole } from "@/lib/types";

export default function Navbar() {
  const [user, setUser] = useState<User>(api.getCurrentUser());
  const [dropdownOpen, setDropdownOpen] = useState(false);

  useEffect(() => {
    setUser(api.getCurrentUser());
  }, []);

  const handleRoleChange = (role: UserRole) => {
    api.setRole(role);
    setUser(api.getCurrentUser());
    setDropdownOpen(false);
    // Trigger custom event for components listening to role updates
    if (typeof window !== "undefined") {
      window.dispatchEvent(new Event("roleChanged"));
    }
  };

  return (
    <header className="h-16 border-b border-slate-800 bg-navy-900/90 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-40">
      {/* Brand & Market Identity */}
      <div className="flex items-center space-x-4">
        <Link href="/" className="flex items-center space-x-3">
          <div className="h-9 w-9 rounded-lg bg-gradient-to-tr from-tbo-600 to-indigo-500 flex items-center justify-center text-white font-bold shadow-lg shadow-tbo-500/20">
            IQ
          </div>
          <div className="flex flex-col">
            <div className="flex items-center space-x-2">
              <span className="font-bold text-lg text-slate-100 tracking-tight">
                Inven<span className="text-tbo-400">IQ</span>
              </span>
              <span className="text-[10px] uppercase font-semibold tracking-wider px-2 py-0.5 rounded bg-tbo-500/10 text-tbo-300 border border-tbo-500/20">
                TBO.COM B2B
              </span>
            </div>
            <span className="text-[11px] text-slate-400">
              Inventory Optimization & Stochastic Risk Engine
            </span>
          </div>
        </Link>
      </div>

      {/* Center Operational Status */}
      <div className="hidden md:flex items-center space-x-6 text-xs text-slate-400">
        <div className="flex items-center space-x-2">
          <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span>HiGHS MILP Engine: Online</span>
        </div>
        <div className="flex items-center space-x-2">
          <Activity className="h-3.5 w-3.5 text-tbo-400" />
          <span>LightGBM Quantile Forecast: v2.1</span>
        </div>
        <div className="flex items-center space-x-2">
          <Layers className="h-3.5 w-3.5 text-indigo-400" />
          <span>Lakehouse: 11 Tables Synchronized</span>
        </div>
      </div>

      {/* Right: Role Switcher & Persona Avatar */}
      <div className="flex items-center space-x-4">
        <div className="relative">
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="flex items-center space-x-3 px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800/80 hover:bg-slate-800 transition text-left"
          >
            <div className="h-8 w-8 rounded-full bg-gradient-to-br from-indigo-500 to-tbo-600 flex items-center justify-center text-white text-xs font-bold">
              {user.full_name
                .split(" ")
                .map((n) => n[0])
                .join("")
                .slice(0, 2)}
            </div>
            <div className="hidden sm:flex flex-col">
              <span className="text-xs font-medium text-slate-200">
                {user.full_name}
              </span>
              <span className="text-[10px] uppercase font-semibold text-tbo-400">
                {user.role.replace("_", " ")}
              </span>
            </div>
            <ChevronDown className="h-4 w-4 text-slate-400 ml-1" />
          </button>

          {dropdownOpen && (
            <div className="absolute right-0 mt-2 w-64 rounded-xl border border-slate-800 bg-slate-900 shadow-2xl p-2 z-50">
              <div className="px-3 py-2 border-b border-slate-800 mb-1">
                <p className="text-xs font-semibold text-slate-200">
                  Switch Active Role (RBAC)
                </p>
                <p className="text-[11px] text-slate-400">
                  Test permissions & approval controls
                </p>
              </div>

              <button
                onClick={() => handleRoleChange("buyer")}
                className={`w-full flex items-center space-x-2.5 px-3 py-2 rounded-lg text-xs text-left transition ${
                  user.role === "buyer"
                    ? "bg-tbo-600/20 text-tbo-300 font-medium"
                    : "text-slate-300 hover:bg-slate-800"
                }`}
              >
                <UserCheck className="h-4 w-4 text-tbo-400" />
                <div>
                  <div className="font-semibold">Procurement Buyer</div>
                  <div className="text-[10px] text-slate-400">
                    Submit runs, review inventory
                  </div>
                </div>
              </button>

              <button
                onClick={() => handleRoleChange("analyst")}
                className={`w-full flex items-center space-x-2.5 px-3 py-2 rounded-lg text-xs text-left transition ${
                  user.role === "analyst"
                    ? "bg-tbo-600/20 text-tbo-300 font-medium"
                    : "text-slate-300 hover:bg-slate-800"
                }`}
              >
                <Activity className="h-4 w-4 text-indigo-400" />
                <div>
                  <div className="font-semibold">Revenue Analyst</div>
                  <div className="text-[10px] text-slate-400">
                    What-if simulator & price elasticity
                  </div>
                </div>
              </button>

              <button
                onClick={() => handleRoleChange("finance_approver")}
                className={`w-full flex items-center space-x-2.5 px-3 py-2 rounded-lg text-xs text-left transition ${
                  user.role === "finance_approver"
                    ? "bg-tbo-600/20 text-tbo-300 font-medium"
                    : "text-slate-300 hover:bg-slate-800"
                }`}
              >
                <ShieldCheck className="h-4 w-4 text-emerald-400" />
                <div>
                  <div className="font-semibold">Finance & Risk Head</div>
                  <div className="text-[10px] text-slate-400">
                    Authorize ₹ pre-buys & audit log
                  </div>
                </div>
              </button>

              <button
                onClick={() => handleRoleChange("admin")}
                className={`w-full flex items-center space-x-2.5 px-3 py-2 rounded-lg text-xs text-left transition ${
                  user.role === "admin"
                    ? "bg-tbo-600/20 text-tbo-300 font-medium"
                    : "text-slate-300 hover:bg-slate-800"
                }`}
              >
                <ShieldCheck className="h-4 w-4 text-amber-400" />
                <div>
                  <div className="font-semibold">Administrator</div>
                  <div className="text-[10px] text-slate-400">
                    Full superuser capabilities
                  </div>
                </div>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
