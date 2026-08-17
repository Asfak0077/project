"use client";

import { motion } from "framer-motion";
import { CheckCircle, AlertCircle, Zap, ShieldAlert } from "lucide-react";

interface Laptop {
  laptop_id: string;
  Brand: string;
  Processor: string;
  RAM_GB: number;
  Price_Clean: number;
  "Dedicated Graphics": string;
}

interface ComparisonMatrixProps {
  products: Laptop[];
  noMatch: boolean;
}

export default function ComparisonMatrix({
  products,
  noMatch,
}: ComparisonMatrixProps) {
  if (noMatch) {
    return (
      <div className="max-w-2xl mx-auto my-12 p-8 glass-panel border border-red-500/30 rounded-3xl text-center">
        <ShieldAlert className="w-12 h-12 text-red-400 mx-auto mb-3 animate-bounce" />
        <h3 className="text-xl font-bold text-white mb-2">
          No Product Available
        </h3>
        <p className="text-slate-400 text-sm">
          Strict Anti-Hallucination Guardrail Active: No products in our
          database met your exact specifications. Please try broadening your
          search constraints.
        </p>
      </div>
    );
  }

  if (products.length === 0) return null;

  return (
    <section className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-white flex items-center gap-2">
          <span>Side-by-Side Spec Comparison</span>
          <span className="text-xs px-2.5 py-1 bg-purple-500/20 text-purple-300 border border-purple-500/30 rounded-full font-normal">
            Comparing {products.length} Products
          </span>
        </h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {products.map((item, index) => {
          const isBestValue = item.Price_Clean <= 50000;
          const isHighPerformance =
            item.RAM_GB >= 16 || item["Dedicated Graphics"] !== "0";

          return (
            <motion.div
              key={item.laptop_id}
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1, duration: 0.4 }}
              className="glass-panel glass-panel-hover rounded-3xl p-6 flex flex-col justify-between relative overflow-hidden transition-all"
            >
              {/* Badges */}
              <div className="flex items-center justify-between mb-4">
                <span className="text-xs font-mono font-bold text-purple-400 bg-purple-950/60 border border-purple-800/50 px-2.5 py-1 rounded-lg">
                  {item.laptop_id}
                </span>
                {isHighPerformance && (
                  <span className="text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 px-2.5 py-1 rounded-full flex items-center gap-1">
                    <Zap className="w-3 h-3 text-emerald-400" /> High
                    Performance
                  </span>
                )}
              </div>

              {/* Title & Price */}
              <div className="mb-6">
                <h3 className="text-xl font-bold text-white mb-1">
                  {item.Brand} Laptop
                </h3>
                <p className="text-slate-400 text-sm mb-3">{item.Processor}</p>
                <div className="text-2xl font-black text-white">
                  ₹{item.Price_Clean.toLocaleString("en-IN")}
                </div>
              </div>

              {/* Spec Bars */}
              <div className="space-y-4 mb-6">
                {/* RAM Spec Bar */}
                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-slate-400">RAM Capacity</span>
                    <span className="font-semibold text-white">
                      {item.RAM_GB} GB
                    </span>
                  </div>
                  <div className="w-full bg-slate-900 rounded-full h-2 border border-slate-800">
                    <div
                      className="bg-gradient-to-r from-purple-500 to-blue-500 h-2 rounded-full transition-all duration-1000"
                      style={{
                        width: `${Math.min((item.RAM_GB / 32) * 100, 100)}%`,
                      }}
                    />
                  </div>
                </div>

                {/* GPU Capability */}
                <div className="flex items-center justify-between text-xs p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                  <span className="text-slate-400">Dedicated GPU:</span>
                  <span
                    className={`font-semibold ${item["Dedicated Graphics"] !== "0" ? "text-emerald-400" : "text-slate-500"}`}
                  >
                    {item["Dedicated Graphics"] !== "0"
                      ? item["Dedicated Graphics"]
                      : "None (Integrated)"}
                  </span>
                </div>
              </div>

              {/* Action Button */}
              <button className="w-full py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 font-medium text-sm hover:border-purple-500 hover:text-white transition-all flex items-center justify-center gap-2">
                <CheckCircle className="w-4 h-4 text-purple-400" />
                <span>Select for AI Chat Analysis</span>
              </button>
            </motion.div>
          );
        })}
      </div>
    </section>
  );
}
