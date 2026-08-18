"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Swords,
  Trophy,
  Flame,
  DollarSign,
  Monitor,
  BatteryCharging,
  Star,
  Sparkles,
  ShieldCheck,
  RotateCcw,
  CheckCircle2,
  ArrowRight,
  History,
  Zap,
  Scale,
  MessageSquare,
  Award,
} from "lucide-react";
import { Product, BattleResultData, BattleRound } from "../types";
import { runProductBattle, getBattleHistory } from "../../services/api";
import { getProductImage, formatRamDisplay } from "../../utils/imageHelper";

interface BattleViewProps {
  shortlisted: Product[];
  onNavigate: (view: string, tab?: string) => void;
  onAskAI?: (query: string) => void;
}

export default function BattleView({
  shortlisted,
  onNavigate,
  onAskAI,
}: BattleViewProps) {
  const [selectedP1, setSelectedP1] = useState<Product | null>(null);
  const [selectedP2, setSelectedP2] = useState<Product | null>(null);
  const [catalogProducts, setCatalogProducts] = useState<Product[]>([]);
  const [battleData, setBattleData] = useState<BattleResultData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [activeRound, setActiveRound] = useState<number>(0);
  const [showHistoryModal, setShowHistoryModal] = useState<boolean>(false);
  const [pastBattles, setPastBattles] = useState<BattleResultData[]>([]);
  const [loadingHistory, setLoadingHistory] = useState<boolean>(false);

  // Load catalog products for dropdown selection
  useEffect(() => {
    import("../../services/api").then(({ getProducts }) => {
      getProducts({ limit: 40 })
        .then((data) => {
          if (data?.items?.length) {
            setCatalogProducts(data.items);
          }
        })
        .catch(() => {});
    });
  }, []);

  // Compute available fighters pool (shortlisted + catalog products deduplicated)
  const availableFighters = React.useMemo(() => {
    const map = new Map<string, Product>();
    (shortlisted || []).forEach((p) => map.set(String(p.id), p));
    (catalogProducts || []).forEach((p) => {
      if (!map.has(String(p.id))) {
        map.set(String(p.id), p);
      }
    });
    return Array.from(map.values());
  }, [shortlisted, catalogProducts]);

  // Auto-select distinct products for Product A and Product B
  useEffect(() => {
    if (availableFighters.length >= 2) {
      if (!selectedP1) {
        setSelectedP1(availableFighters[0]);
      }
      if (!selectedP2) {
        // Find first product that has a different ID
        const second = availableFighters.find((p) => String(p.id) !== String(selectedP1?.id || availableFighters[0].id));
        if (second) setSelectedP2(second);
      }
    } else if (availableFighters.length === 1) {
      if (!selectedP1) setSelectedP1(availableFighters[0]);
    }
  }, [availableFighters, selectedP1, selectedP2]);

  const isSameProduct = Boolean(
    selectedP1 && selectedP2 && String(selectedP1.id) === String(selectedP2.id)
  );

  // Launch Battle
  const handleStartBattle = async (p1?: Product, p2?: Product) => {
    const fighter1 = p1 || selectedP1;
    const fighter2 = p2 || selectedP2;

    if (!fighter1 || !fighter2) {
      setErrorMessage("Please select 2 products to enter the AI Battle Arena.");
      return;
    }

    if (String(fighter1.id) === String(fighter2.id)) {
      setErrorMessage("Cannot battle a product against itself. Please switch Product B to a different device.");
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);
    setBattleData(null);
    setActiveRound(0);

    try {
      const res = await runProductBattle([fighter1.id, fighter2.id]);
      setBattleData(res);
      // Auto-step through rounds with smooth interval
      let step = 1;
      const interval = setInterval(() => {
        if (step <= 5) {
          setActiveRound(step);
          step += 1;
        } else {
          clearInterval(interval);
        }
      }, 650);
    } catch (err: any) {
      setErrorMessage(err.message || "Unable to start battle. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleFetchHistory = async () => {
    setLoadingHistory(true);
    setShowHistoryModal(true);
    try {
      const res = await getBattleHistory(15, 0);
      setPastBattles(res.battles || []);
    } catch (err) {
      console.warn("Could not load battle history:", err);
    } finally {
      setLoadingHistory(false);
    }
  };

  const getRoundIcon = (rNum: number) => {
    switch (rNum) {
      case 1: return Flame;
      case 2: return DollarSign;
      case 3: return Monitor;
      case 4: return BatteryCharging;
      case 5: return Star;
      default: return Sparkles;
    }
  };

  const getRoundBarColor = (rNum: number) => {
    switch (rNum) {
      case 1: return "bg-blue-500";
      case 2: return "bg-emerald-500";
      case 3: return "bg-violet-500";
      case 4: return "bg-amber-500";
      case 5: return "bg-rose-500";
      default: return "bg-blue-500";
    }
  };

  const getRoundIconBg = (rNum: number) => {
    switch (rNum) {
      case 1: return "bg-blue-50 text-blue-600 border border-blue-200";
      case 2: return "bg-emerald-50 text-emerald-600 border border-emerald-200";
      case 3: return "bg-violet-50 text-violet-600 border border-violet-200";
      case 4: return "bg-amber-50 text-amber-600 border border-amber-200";
      case 5: return "bg-rose-50 text-rose-600 border border-rose-200";
      default: return "bg-slate-50 text-slate-600 border border-slate-200";
    }
  };

  return (
    <div className="py-6 space-y-8 pb-32">
      {/* ─── Hero Header Card ─── */}
      <motion.div
        initial={{ opacity: 0, y: -15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="p-6 sm:p-8 rounded-3xl bg-white border border-slate-200 shadow-sm"
      >
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-blue-50 border border-blue-200 text-blue-700 text-[11px] font-extrabold uppercase tracking-wider mb-3 shadow-xs">
              <ShieldCheck className="w-3.5 h-3.5 text-blue-600" />
              RAG Verified • AI Judge Engine
            </div>
            <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-blue-600 to-violet-600 flex items-center justify-center text-white shadow-md shadow-blue-600/25 shrink-0">
                <Swords className="w-5 h-5" />
              </div>
              AI Product Battle Arena
            </h1>
            <p className="text-sm text-slate-600 mt-2 max-w-xl font-medium leading-relaxed">
              Real-time multi-dimensional scoring across Performance, Value, Display, Battery, and Verified Community Ratings.
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <button
              onClick={handleFetchHistory}
              className="px-4 py-2.5 rounded-xl bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 hover:border-slate-300 text-xs font-bold transition-all hover:shadow-sm flex items-center gap-2 cursor-pointer"
            >
              <History className="w-4 h-4 text-violet-600" />
              Battle History
            </button>

            <button
              onClick={() => onNavigate("compare")}
              className="px-4 py-2.5 rounded-xl bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200 hover:border-blue-300 text-xs font-bold transition-all hover:shadow-sm flex items-center gap-2 cursor-pointer"
            >
              <Scale className="w-4 h-4" />
              Matrix View
            </button>
          </div>
        </div>
      </motion.div>

      {/* Error Notification */}
      <AnimatePresence>
        {errorMessage && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-700 text-sm font-semibold flex items-center justify-between shadow-xs"
          >
            <span>{errorMessage}</span>
            <button
              onClick={() => setErrorMessage(null)}
              className="text-xs text-rose-600 hover:text-rose-800 underline font-bold"
            >
              Dismiss
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ─── Fighter Selection Stage Cards ─── */}
      <div className="grid grid-cols-1 lg:grid-cols-11 gap-6 items-stretch">
        {/* Product A Card */}
        <div className="lg:col-span-5">
          <motion.div
            initial={{ opacity: 0, x: -25 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5 }}
            className="relative h-full p-6 rounded-3xl bg-white border-2 border-blue-200 hover:border-blue-400 shadow-sm hover:shadow-md transition-all flex flex-col justify-between overflow-hidden group"
          >
            <div className="absolute top-0 right-0 px-4 py-1.5 rounded-bl-2xl bg-blue-600 text-white font-extrabold text-[11px] uppercase tracking-wider shadow-xs">
              Product A
            </div>

            {selectedP1 ? (
              <div className="flex flex-col sm:flex-row gap-5 items-center my-auto">
                <div className="w-28 h-28 rounded-2xl overflow-hidden bg-slate-50 border border-slate-200 shrink-0 p-3 flex items-center justify-center">
                  <img
                    src={getProductImage(selectedP1)}
                    alt={selectedP1.name}
                    className="w-full h-full object-contain group-hover:scale-105 transition-transform duration-300"
                  />
                </div>

                <div className="flex-1 text-center sm:text-left min-w-0">
                  <div className="text-[11px] font-extrabold text-blue-600 uppercase tracking-widest">
                    {selectedP1.brand} • {selectedP1.category}
                  </div>
                  <h3 className="text-base font-extrabold text-slate-900 mt-0.5 line-clamp-2">
                    {selectedP1.name}
                  </h3>
                  <div className="text-lg font-black text-emerald-600 mt-1">
                    ₹{selectedP1.price?.toLocaleString()}
                  </div>
                  <div className="text-xs text-slate-600 mt-2 flex flex-wrap gap-1.5">
                    <span className="bg-slate-100 px-2 py-0.5 rounded-md border border-slate-200 font-mono text-[11px] font-semibold text-slate-700">
                      {selectedP1.cpu || "CPU N/A"}
                    </span>
                    <span className="bg-slate-100 px-2 py-0.5 rounded-md border border-slate-200 font-mono text-[11px] font-semibold text-slate-700">
                      {formatRamDisplay(selectedP1.ram)}
                    </span>
                  </div>
                </div>

                {battleData && (
                  <div className="sm:text-right border-t sm:border-t-0 sm:border-l border-slate-200 pt-3 sm:pt-0 sm:pl-4 shrink-0">
                    <div className="text-[10px] font-extrabold text-slate-400 uppercase">AI Score</div>
                    <div className="text-3xl font-black text-blue-600">
                      {battleData.product_1_score}
                      <span className="text-xs text-slate-400 font-normal">/100</span>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="py-12 px-6 rounded-2xl border-2 border-dashed border-slate-300 bg-slate-50/70 text-center my-auto">
                <div className="w-12 h-12 mx-auto mb-3 rounded-2xl bg-blue-50 border border-blue-200 flex items-center justify-center">
                  <Sparkles className="w-5 h-5 text-blue-600" />
                </div>
                <div className="font-extrabold text-slate-700 text-sm">Select Product A</div>
                <p className="text-xs text-slate-500 mt-1">Choose from your shortlisted devices or catalog</p>
              </div>
            )}

            {/* Selector dropdown to switch Product A */}
            {availableFighters.length > 1 && (
              <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between gap-2">
                <span className="text-xs text-slate-500 font-bold shrink-0">Switch Product A:</span>
                <select
                  value={selectedP1?.id || ""}
                  onChange={(e) => {
                    const p = availableFighters.find((item) => String(item.id) === e.target.value);
                    if (p) setSelectedP1(p);
                  }}
                  className="bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs text-slate-800 font-semibold focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-400 w-full max-w-[260px] truncate"
                >
                  {availableFighters.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.brand} {p.name} (₹{p.price?.toLocaleString()})
                    </option>
                  ))}
                </select>
              </div>
            )}
          </motion.div>
        </div>

        {/* VS Emblem */}
        <div className="lg:col-span-1 flex flex-col items-center justify-center my-2 lg:my-0">
          <motion.div
            animate={{ scale: [1, 1.06, 1] }}
            transition={{ repeat: Infinity, duration: 2.5, ease: "easeInOut" }}
            className="w-14 h-14 rounded-2xl flex items-center justify-center text-white font-black text-lg shadow-lg border border-white"
            style={{
              background: "linear-gradient(135deg, #2563EB, #7C3AED, #EC4899)",
              boxShadow: "0 6px 20px rgba(124, 58, 237, 0.25)",
            }}
          >
            VS
          </motion.div>
          <span className="text-[10px] font-black text-slate-400 mt-2 uppercase tracking-wider">AI Judge</span>
        </div>

        {/* Product B Card */}
        <div className="lg:col-span-5">
          <motion.div
            initial={{ opacity: 0, x: 25 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5 }}
            className="relative h-full p-6 rounded-3xl bg-white border-2 border-rose-200 hover:border-rose-400 shadow-sm hover:shadow-md transition-all flex flex-col justify-between overflow-hidden group"
          >
            <div className="absolute top-0 right-0 px-4 py-1.5 rounded-bl-2xl bg-rose-600 text-white font-extrabold text-[11px] uppercase tracking-wider shadow-xs">
              Product B
            </div>

            {selectedP2 ? (
              <div className="flex flex-col sm:flex-row gap-5 items-center my-auto">
                <div className="w-28 h-28 rounded-2xl overflow-hidden bg-slate-50 border border-slate-200 shrink-0 p-3 flex items-center justify-center">
                  <img
                    src={getProductImage(selectedP2)}
                    alt={selectedP2.name}
                    className="w-full h-full object-contain group-hover:scale-105 transition-transform duration-300"
                  />
                </div>

                <div className="flex-1 text-center sm:text-left min-w-0">
                  <div className="text-[11px] font-extrabold text-rose-600 uppercase tracking-widest">
                    {selectedP2.brand} • {selectedP2.category}
                  </div>
                  <h3 className="text-base font-extrabold text-slate-900 mt-0.5 line-clamp-2">
                    {selectedP2.name}
                  </h3>
                  <div className="text-lg font-black text-emerald-600 mt-1">
                    ₹{selectedP2.price?.toLocaleString()}
                  </div>
                  <div className="text-xs text-slate-600 mt-2 flex flex-wrap gap-1.5">
                    <span className="bg-slate-100 px-2 py-0.5 rounded-md border border-slate-200 font-mono text-[11px] font-semibold text-slate-700">
                      {selectedP2.cpu || "CPU N/A"}
                    </span>
                    <span className="bg-slate-100 px-2 py-0.5 rounded-md border border-slate-200 font-mono text-[11px] font-semibold text-slate-700">
                      {formatRamDisplay(selectedP2.ram)}
                    </span>
                  </div>
                </div>

                {battleData && (
                  <div className="sm:text-right border-t sm:border-t-0 sm:border-l border-slate-200 pt-3 sm:pt-0 sm:pl-4 shrink-0">
                    <div className="text-[10px] font-extrabold text-slate-400 uppercase">AI Score</div>
                    <div className="text-3xl font-black text-rose-600">
                      {battleData.product_2_score}
                      <span className="text-xs text-slate-400 font-normal">/100</span>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="py-12 px-6 rounded-2xl border-2 border-dashed border-slate-300 bg-slate-50/70 text-center my-auto">
                <div className="w-12 h-12 mx-auto mb-3 rounded-2xl bg-rose-50 border border-rose-200 flex items-center justify-center">
                  <Sparkles className="w-5 h-5 text-rose-600" />
                </div>
                <div className="font-extrabold text-slate-700 text-sm">Select Product B</div>
                <p className="text-xs text-slate-500 mt-1">Choose from your shortlisted devices or catalog</p>
              </div>
            )}

            {/* Selector dropdown to switch Product B */}
            {availableFighters.length > 1 && (
              <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between gap-2">
                <span className="text-xs text-slate-500 font-bold shrink-0">Switch Product B:</span>
                <select
                  value={selectedP2?.id || ""}
                  onChange={(e) => {
                    const p = availableFighters.find((item) => String(item.id) === e.target.value);
                    if (p) setSelectedP2(p);
                  }}
                  className="bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs text-slate-800 font-semibold focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-400 w-full max-w-[260px] truncate"
                >
                  {availableFighters.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.brand} {p.name} (₹{p.price?.toLocaleString()})
                    </option>
                  ))}
                </select>
              </div>
            )}
          </motion.div>
        </div>
      </div>

      {/* Warning banner when same product is chosen on both sides */}
      {isSameProduct && (
        <div className="p-3.5 rounded-2xl bg-amber-50 border border-amber-200 text-amber-800 text-xs font-bold flex items-center justify-center gap-2 shadow-xs">
          <span>⚠️ Both slots currently have the same product selected. Please switch Product B to a different item to start the AI Battle.</span>
        </div>
      )}

      {/* ─── Start Battle Action Button ─── */}
      <div className="flex justify-center">
        <motion.button
          whileHover={{ scale: isSameProduct ? 1 : 1.03 }}
          whileTap={{ scale: isSameProduct ? 1 : 0.97 }}
          onClick={() => handleStartBattle()}
          disabled={isLoading || !selectedP1 || !selectedP2 || isSameProduct}
          className={`px-10 py-4 rounded-2xl font-black text-sm uppercase tracking-wider flex items-center gap-3 transition-all duration-200 ${
            isLoading || isSameProduct || !selectedP1 || !selectedP2
              ? "bg-slate-200 text-slate-400 cursor-not-allowed shadow-none"
              : "text-white shadow-xl hover:shadow-2xl cursor-pointer"
          }`}
          style={
            isLoading || isSameProduct || !selectedP1 || !selectedP2
              ? {}
              : {
                  background: "linear-gradient(135deg, #2563EB, #7C3AED)",
                  boxShadow: "0 8px 30px rgba(37,99,235,0.28)",
                }
          }
        >
          {isLoading ? (
            <>
              <div className="w-5 h-5 border-2 border-slate-300 border-t-slate-600 rounded-full animate-spin" />
              <span>AI Judge Evaluating Specs...</span>
            </>
          ) : (
            <>
              <Swords className="w-5 h-5" />
              <span>{battleData ? "Re-Run AI Battle" : "Start AI Battle ⚡"}</span>
            </>
          )}
        </motion.button>
      </div>

      {/* ─── 5-Round Battle Results Showcase ─── */}
      {battleData && (
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="space-y-6"
        >
          {/* Grand Winner Announcement Card */}
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, duration: 0.5 }}
            className="p-6 sm:p-8 rounded-3xl bg-white border-2 border-amber-300 shadow-md relative overflow-hidden"
          >
            <div
              className="absolute top-0 right-0 w-80 h-80 rounded-full pointer-events-none opacity-30"
              style={{ background: "radial-gradient(circle, rgba(245,158,11,0.2), transparent 70%)" }}
            />

            <div className="flex flex-col md:flex-row items-center justify-between gap-6 relative z-10">
              <div className="flex items-center gap-5">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-amber-400 via-amber-500 to-yellow-300 flex items-center justify-center text-white shadow-lg shadow-amber-400/30 shrink-0">
                  <Trophy className="w-9 h-9" />
                </div>

                <div>
                  <div className="text-[11px] font-black text-amber-600 uppercase tracking-widest">
                    AI Judge Decision • {battleData.confidence} Confidence
                  </div>
                  <h2 className="text-2xl sm:text-3xl font-black text-slate-900 mt-1">
                    🏆 Winner: {battleData.winner_name}
                  </h2>
                  <p className="text-sm text-slate-600 mt-1 max-w-2xl font-medium leading-relaxed">
                    {battleData.ai_verdict.summary}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3 shrink-0">
                <button
                  onClick={() => {
                    if (onAskAI) {
                      onAskAI(`Why did ${battleData.winner_name} win the battle?`);
                    }
                    onNavigate("chat");
                  }}
                  className="px-5 py-3 rounded-xl text-white text-xs font-black transition-all flex items-center gap-2 shadow-lg cursor-pointer hover:shadow-xl hover:scale-105 active:scale-95"
                  style={{
                    background: "linear-gradient(135deg, #2563EB, #7C3AED)",
                    boxShadow: "0 4px 20px rgba(37,99,235,0.25)",
                  }}
                >
                  <MessageSquare className="w-4 h-4" />
                  Deep Dive in AI Chat
                </button>
              </div>
            </div>

            {/* Key Reasons Chips */}
            <div className="mt-6 pt-6 border-t border-slate-100 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
              {battleData.key_reasons.map((kr, idx) => (
                <div
                  key={idx}
                  className="flex items-start gap-2.5 p-3.5 rounded-xl bg-emerald-50/70 border border-emerald-200 text-xs text-slate-800"
                >
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  <span className="font-semibold">{kr}</span>
                </div>
              ))}
            </div>
          </motion.div>

          {/* ─── The 5 Rounds Breakdown ─── */}
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            {battleData.rounds.map((r, idx) => {
              const IconComponent = getRoundIcon(r.round_number);
              const barColor = getRoundBarColor(r.round_number);
              const iconBg = getRoundIconBg(r.round_number);

              return (
                <motion.div
                  key={r.round_number}
                  initial={{ opacity: 0, y: 15 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.1 }}
                  className={`p-5 rounded-2xl bg-white border-2 transition-all duration-300 hover:shadow-lg hover:-translate-y-0.5 ${
                    r.winner === "p1"
                      ? "border-blue-300 shadow-xs"
                      : r.winner === "p2"
                      ? "border-rose-300 shadow-xs"
                      : "border-slate-200 shadow-xs"
                  }`}
                >
                  {/* Round Header */}
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${iconBg}`}>
                        <IconComponent className="w-4 h-4" />
                      </div>
                      <span className="text-[11px] font-black text-slate-500 uppercase">
                        R{r.round_number}
                      </span>
                    </div>
                    <span className="text-[10px] font-extrabold text-slate-600 bg-slate-100 px-2 py-0.5 rounded-md border border-slate-200">
                      {r.weight}
                    </span>
                  </div>

                  <h4 className="text-sm font-black text-slate-900 mb-3">{r.title}</h4>

                  {/* Score Comparison Bars */}
                  <div className="space-y-2.5 mb-3">
                    <div>
                      <div className="flex justify-between text-[11px] font-extrabold mb-1">
                        <span className="text-blue-600">{battleData.product_1.brand}</span>
                        <span className="text-blue-600 font-mono">{r.p1_score}</span>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden border border-slate-200">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${r.p1_score}%` }}
                          transition={{ duration: 0.8, delay: idx * 0.12 }}
                          className="bg-blue-600 h-2 rounded-full"
                        />
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between text-[11px] font-extrabold mb-1">
                        <span className="text-rose-600">{battleData.product_2.brand}</span>
                        <span className="text-rose-600 font-mono">{r.p2_score}</span>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden border border-slate-200">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${r.p2_score}%` }}
                          transition={{ duration: 0.8, delay: idx * 0.12 + 0.1 }}
                          className="bg-rose-600 h-2 rounded-full"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Winner Badge */}
                  <div className="pt-2.5 border-t border-slate-100">
                    <div className="text-[10px] font-extrabold text-slate-400 uppercase">Round Winner</div>
                    <div className="text-xs font-black text-amber-700 flex items-center gap-1 mt-0.5">
                      <Award className="w-3.5 h-3.5 text-amber-600" />
                      {r.winner_name}
                    </div>
                    <p className="text-[11px] text-slate-600 mt-1 leading-tight line-clamp-2 font-medium">
                      {r.reason}
                    </p>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </motion.div>
      )}

      {/* ─── Past Battles Modal ─── */}
      {showHistoryModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="w-full max-w-2xl bg-white border border-slate-200 rounded-3xl p-6 max-h-[85vh] flex flex-col shadow-2xl"
          >
            <div className="flex items-center justify-between border-b border-slate-200 pb-4 mb-4">
              <h3 className="text-lg font-black text-slate-900 flex items-center gap-2">
                <History className="w-5 h-5 text-violet-600" />
                Previous Battle Match-ups
              </h3>
              <button
                onClick={() => setShowHistoryModal(false)}
                className="text-xs font-bold text-slate-500 hover:text-slate-900 px-3 py-1.5 rounded-lg hover:bg-slate-100 transition cursor-pointer"
              >
                ✕ Close
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-3 pr-1">
              {loadingHistory ? (
                <div className="py-12 text-center text-slate-500 text-sm">
                  <div className="w-6 h-6 border-2 border-slate-200 border-t-blue-600 rounded-full animate-spin mx-auto mb-3" />
                  Loading battle history...
                </div>
              ) : pastBattles.length === 0 ? (
                <div className="py-12 text-center text-slate-500 text-sm">
                  <Swords className="w-10 h-10 text-slate-300 mx-auto mb-3" />
                  No battles recorded yet. Launch your first match-up!
                </div>
              ) : (
                pastBattles.map((b, idx) => (
                  <div
                    key={b.battle_id || idx}
                    onClick={() => {
                      setBattleData(b);
                      setShowHistoryModal(false);
                    }}
                    className="p-4 rounded-2xl bg-slate-50 border border-slate-200 hover:border-blue-400 hover:shadow-md transition-all cursor-pointer flex items-center justify-between group"
                  >
                    <div>
                      <div className="text-sm font-black text-slate-900">
                        {b.product_1_name} ({b.product_1_score}) vs {b.product_2_name} ({b.product_2_score})
                      </div>
                      <div className="text-xs text-amber-600 font-bold mt-1 flex items-center gap-1">
                        <Trophy className="w-3.5 h-3.5" /> Winner: {b.winner_name}
                      </div>
                    </div>

                    <div className="text-right">
                      <span className="text-[10px] text-slate-400 font-medium">
                        {b.created_at ? new Date(b.created_at).toLocaleDateString() : "Recent"}
                      </span>
                      <div className="text-xs text-blue-600 font-bold mt-1 group-hover:underline">Replay →</div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </motion.div>
        </div>
      )}
    </div>
  );
}
