"use client";

import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  Sparkles,
  Award,
  FileDown,
  Trash2,
  Trophy,
  Check,
  Zap,
  Battery,
  SlidersHorizontal,
  Loader2,
} from "lucide-react";
import { Product } from "../types";
import { compareProducts, CompareResponseData, SpecComparisonRow } from "../../services/api";
import { useComparison } from "../../context/ComparisonContext";

interface CompareViewProps {
  products: Product[];
  onBack: () => void;
  onLaunchChat: () => void;
  onRemove: (id: string) => void;
}

export default function CompareView({
  products,
  onBack,
  onLaunchChat,
  onRemove,
}: CompareViewProps) {
  const { comparisonResult: contextCompResult, setComparisonResult } = useComparison();
  const [comparisonData, setComparisonData] = useState<CompareResponseData | null>(contextCompResult || null);
  const [loading, setLoading] = useState(false);
  const [onlyDifferences, setOnlyDifferences] = useState(false);
  const [highlightWinners, setHighlightWinners] = useState(true);
  const [exported, setExported] = useState(false);

  // Battery Estimator State
  const [workload, setWorkload] = useState<"light" | "medium" | "heavy">("medium");

  // Keep local state in sync with context
  useEffect(() => {
    if (contextCompResult) {
      setComparisonData(contextCompResult);
    }
  }, [contextCompResult]);

  // Stable ref to track which product IDs we've already fetched for
  const fetchedForIdsRef = React.useRef<string>("");

  // Fetch live comparison spec matrix from FastAPI backend
  useEffect(() => {
    if (products.length === 0) return;
    const currentIds = products.map((p) => p.id).sort().join(",");
    // Only fetch if the product set actually changed
    if (currentIds === fetchedForIdsRef.current) return;
    fetchedForIdsRef.current = currentIds;

    setLoading(true);
    const productIds = products.map((p) => p.id);
    compareProducts(productIds)
      .then((data) => {
        setComparisonData(data);
        setComparisonResult(data);
      })
      .catch((err) => {
        console.error("Comparison API error:", err);
      })
      .finally(() => setLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [products]);

  if (products.length === 0) {
    return (
      <div className="py-24 text-center space-y-4">
        <div className="w-20 h-20 bg-blue-50 border border-blue-200 text-blue-600 rounded-3xl mx-auto flex items-center justify-center">
          <Sparkles className="w-8 h-8 text-blue-600" />
        </div>
        <h2 className="text-2xl font-black text-slate-900">No Products Selected</h2>
        <p className="text-slate-500 text-sm max-w-md mx-auto font-medium">
          Select at least 2 gadgets from the Discover catalog to generate a side-by-side comparison matrix.
        </p>
        <button
          onClick={onBack}
          className="mt-4 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-2xl font-black text-xs shadow-md shadow-blue-500/20 transition-all inline-flex items-center gap-2 cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4" /> Discover Products
        </button>
      </div>
    );
  }

  const specRows: SpecComparisonRow[] = comparisonData?.spec_rows || [
    { label: "Price (INR)", key: "price", values: Object.fromEntries(products.map((p) => [p.id, `₹${p.price.toLocaleString()}`])), is_different: true },
    { label: "Processor (CPU)", key: "cpu", values: Object.fromEntries(products.map((p) => [p.id, p.cpu])), is_different: true },
    { label: "RAM Memory", key: "ram", values: Object.fromEntries(products.map((p) => [p.id, `${Math.round(p.ram)} GB`])), is_different: true },
    { label: "Storage", key: "storage", values: Object.fromEntries(products.map((p) => [p.id, p.storage])), is_different: true },
    { label: "Graphics (GPU)", key: "gpu", values: Object.fromEntries(products.map((p) => [p.id, p.gpu || "Integrated"])), is_different: true },
    { label: "AI Benchmark Score", key: "score", values: Object.fromEntries(products.map((p) => [p.id, `${p.score} / 100`])), is_different: true },
    { label: "User Rating", key: "rating", values: Object.fromEntries(products.map((p) => [p.id, `⭐ ${p.rating || 4.0}`])), is_different: false },
  ];

  const filteredRows = onlyDifferences ? specRows.filter((r) => r.is_different) : specRows;
  const overallWinner = products.reduce((prev, curr) => (curr.score > prev.score ? curr : prev), products[0]);

  const handleExportReport = () => {
    const title = "=======================================================\n           VERSUS AI PRODUCT COMPARISON REPORT          \n=======================================================\n\n";
    const dateStr = `Generated On: ${new Date().toLocaleString()}\nVerified Ground Truth: AWS RDS MySQL + RAG Docs\n\n`;
    
    const cleanWinnerName = overallWinner.name.toLowerCase().startsWith(overallWinner.brand.toLowerCase() + " ")
      ? overallWinner.name
      : `${overallWinner.brand} ${overallWinner.name}`;
      
    const winnerInfo = `🏆 OVERALL BENCHMARK WINNER:\n   ${cleanWinnerName}\n   Composite Score: ${overallWinner.score}/100\n   Price: ₹${overallWinner.price.toLocaleString()}\n   Summary: ${comparisonData?.winner_summary || "Top ranked device in hardware benchmark efficiency."}\n\n`;
    
    const productList = products.map((p, idx) => {
      const pName = p.name.toLowerCase().startsWith(p.brand.toLowerCase() + " ") ? p.name : `${p.brand} ${p.name}`;
      return [
        `-------------------------------------------------------`,
        `Product #${idx + 1}: ${pName}`,
        `-------------------------------------------------------`,
        `• Category:        ${p.category}`,
        `• Price:           ₹${p.price.toLocaleString()}`,
        `• Processor (CPU): ${p.cpu}`,
        `• Memory (RAM):    ${Math.round(p.ram)} GB`,
        `• Storage:         ${p.storage}`,
        `• Graphics (GPU):  ${p.gpu || "Integrated Graphics"}`,
        `• Display:         ${(p as any).display || "Standard Display"}`,
        `• User Rating:     ${p.rating || 4.2} / 5.0`,
        `• AI Score:        ${p.score} / 100`,
      ].join("\n");
    }).join("\n\n");

    const specTable = [
      `\n\n=======================================================`,
      `SIDE-BY-SIDE SPECIFICATION MATRIX`,
      `=======================================================`,
      ...specRows.map((row) => {
        const valList = products.map((p) => `${p.brand}: ${row.values && row.values[p.id] ? row.values[p.id] : "N/A"}`).join(" | ");
        return `${row.label.padEnd(22)}: ${valList}`;
      }),
    ].join("\n");

    const footer = `\n\n=======================================================\nEnd of Report • Powered by VersusAI Intelligence Engine\n`;

    const reportContent = `${title}${dateStr}${winnerInfo}${productList}${specTable}${footer}`;

    const blob = new Blob([reportContent], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `versus-ai-comparison-report-${new Date().toISOString().slice(0, 10)}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    setExported(true);
    setTimeout(() => setExported(false), 2000);
  };

  const calculateBatteryHours = (product: Product) => {
    let baseHours = 8.0;
    if (product.cpu.includes("M3") || product.cpu.includes("Core Ultra") || product.cpu.includes("Ryzen 7")) {
      baseHours = 10.5;
    }
    if (workload === "light") baseHours *= 1.3;
    if (workload === "heavy") baseHours *= 0.6;
    return baseHours.toFixed(1);
  };

  return (
    <div className="py-8 space-y-8 pb-32">
      {/* Header Controls */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <button
          onClick={onBack}
          className="inline-flex items-center gap-2 px-4 py-2 bg-white hover:bg-slate-50 border border-slate-200 rounded-2xl text-xs font-bold text-slate-800 transition-all cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4 text-blue-600" /> Back to Discover
        </button>

        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => setHighlightWinners(!highlightWinners)}
            className={`px-3 py-2 rounded-xl text-xs font-bold border transition-all flex items-center gap-1.5 cursor-pointer ${
              highlightWinners ? "bg-amber-50 text-amber-900 border-amber-300" : "bg-white text-slate-600 border-slate-200"
            }`}
          >
            <Trophy className="w-3.5 h-3.5 text-amber-500" /> Spec Winners
          </button>

          <button
            onClick={() => setOnlyDifferences(!onlyDifferences)}
            className={`px-3 py-2 rounded-xl text-xs font-bold border transition-all cursor-pointer ${
              onlyDifferences ? "bg-blue-600 text-white border-blue-600" : "bg-white text-slate-600 border-slate-200"
            }`}
          >
            Show Differences Only
          </button>

          <button
            onClick={handleExportReport}
            className="px-3.5 py-2 rounded-xl text-xs font-bold bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 flex items-center gap-1.5 cursor-pointer transition-all shadow-2xs"
            title="Export full comparison report to text file"
          >
            {exported ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-600" /> Exported
              </>
            ) : (
              <>
                <FileDown className="w-3.5 h-3.5 text-blue-600" /> Export Report
              </>
            )}
          </button>

          <button
            onClick={onLaunchChat}
            className="px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl text-xs font-black shadow-md shadow-blue-500/25 flex items-center gap-1.5 cursor-pointer"
          >
            <Sparkles className="w-3.5 h-3.5" /> Deep RAG Analysis
          </button>
        </div>
      </div>

      {/* Top Winner Card Banner */}
      {(() => {
        const cleanWinnerName = overallWinner.name.toLowerCase().startsWith(overallWinner.brand.toLowerCase() + " ")
          ? overallWinner.name
          : `${overallWinner.brand} ${overallWinner.name}`;
        
        return (
          <div className="bg-gradient-to-r from-blue-800 via-indigo-900 to-slate-950 text-white rounded-3xl p-6 sm:p-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6 shadow-2xl border border-blue-500/40 relative overflow-hidden">
            {/* Ambient Background Glow */}
            <div className="absolute top-0 right-1/4 w-72 h-72 bg-blue-500/15 rounded-full blur-3xl pointer-events-none" />
            
            <div className="flex items-center gap-5 relative z-10">
              <div className="w-14 h-14 rounded-2xl bg-amber-400 text-slate-950 flex items-center justify-center font-black shadow-lg shadow-amber-400/20 shrink-0">
                <Award className="w-8 h-8" />
              </div>
              <div>
                <div className="text-[11px] font-black uppercase tracking-wider text-amber-300 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-amber-300" /> Overall Benchmark Leader
                </div>
                <h2 className="text-xl sm:text-2xl font-black text-white tracking-tight mt-0.5">
                  {cleanWinnerName}
                </h2>
                <p className="text-xs sm:text-sm text-blue-100/90 mt-1 max-w-xl font-medium leading-relaxed">
                  {comparisonData?.winner_summary ||
                    `Leads with highest composite spec score (${overallWinner.score}/100) and ${overallWinner.gpu || "integrated graphics"}.`}
                </p>
              </div>
            </div>

            <div className="text-left sm:text-right shrink-0 relative z-10 pt-2 sm:pt-0 border-t sm:border-t-0 border-blue-700/50 w-full sm:w-auto flex sm:flex-col justify-between items-center sm:items-end">
              <div className="text-xs text-blue-200 font-bold uppercase tracking-wider">Top Verified Score</div>
              <div className="text-3xl font-black text-amber-300 drop-shadow-sm">{overallWinner.score} / 100</div>
            </div>
          </div>
        );
      })()}

      {/* Product Cards Header */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
        {products.map((p) => (
          <div
            key={p.id}
            className={`bg-white border rounded-3xl p-5 relative shadow-sm flex flex-col justify-between ${
              p.id === overallWinner.id ? "border-amber-400 ring-2 ring-amber-400/20" : "border-slate-200"
            }`}
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-black text-blue-600 uppercase">{p.brand}</span>
                <button
                  onClick={() => onRemove(p.id)}
                  className="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg transition-colors cursor-pointer"
                  title="Remove product"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>

              <div className="h-36 w-full rounded-2xl overflow-hidden mb-3 bg-slate-100">
                <img src={p.image} alt={p.name} className="w-full h-full object-cover" />
              </div>

              <h3 className="font-extrabold text-sm text-slate-900 line-clamp-1">{p.name}</h3>
              <div className="text-lg font-black text-slate-900 mt-1">₹{p.price.toLocaleString()}</div>
            </div>

            <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between text-xs font-bold text-slate-600">
              <span>Benchmark:</span>
              <span className="text-blue-600 font-black">{p.score}/100</span>
            </div>
          </div>
        ))}
      </div>

      {/* Side-by-Side Spec Comparison Matrix Table */}
      <div className="bg-white border border-slate-200 rounded-3xl overflow-hidden shadow-sm">
        <div className="p-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between font-black text-xs text-slate-700 uppercase tracking-wider">
          <span>Specification Delta Matrix</span>
          <span>{filteredRows.length} Rows</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <tbody>
              {filteredRows.map((row, idx) => (
                <tr
                  key={row.key}
                  className={`border-b border-slate-100 hover:bg-slate-50/80 transition-colors ${
                    idx % 2 === 0 ? "bg-white" : "bg-slate-50/40"
                  }`}
                >
                  <td className="py-4 px-5 font-bold text-slate-600 w-48 bg-slate-50/60 shrink-0">
                    {row.label}
                  </td>
                  {products.map((p) => {
                    const rawVal = row.values ? row.values[p.id] : (row.key ? (p as any)[row.key] : "");
                    const valStr = typeof rawVal === "object" ? JSON.stringify(rawVal) : String(rawVal || "—");
                    const isRowWinner = highlightWinners && row.winner_product_id === p.id;

                    return (
                      <td
                        key={p.id}
                        className={`py-4 px-5 font-semibold text-slate-800 ${
                          isRowWinner ? "bg-amber-50/80 font-black text-amber-900" : ""
                        }`}
                      >
                        <div className="flex items-center gap-1.5">
                          {isRowWinner && <Trophy className="w-3.5 h-3.5 text-amber-600 shrink-0" />}
                          <span>{valStr}</span>
                        </div>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Battery Life Estimator Calculator */}
      <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 space-y-6 shadow-sm">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <Battery className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-extrabold text-base text-slate-900">Workload Runtime Estimator</h3>
              <p className="text-xs text-slate-500 font-medium">Estimated battery hours based on CPU TDP</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {(["light", "medium", "heavy"] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => setWorkload(mode)}
                className={`px-3.5 py-1.5 rounded-xl text-xs font-bold capitalize transition-all cursor-pointer ${
                  workload === mode
                    ? "bg-slate-900 text-white"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                {mode} Load
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {products.map((p) => (
            <div key={p.id} className="p-4 bg-slate-50 border border-slate-200 rounded-2xl">
              <div className="text-xs font-bold text-slate-500 truncate">{p.name}</div>
              <div className="text-2xl font-black text-emerald-600 mt-1">
                {calculateBatteryHours(p)} <span className="text-xs font-semibold text-slate-500">hours</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
