"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, Sparkles, SlidersHorizontal, ArrowRight } from "lucide-react";

interface SearchHeroProps {
  onSearch: (mode: "novice" | "advanced", query: any) => void;
}

export default function SearchHero({ onSearch }: SearchHeroProps) {
  const [mode, setMode] = useState<"novice" | "advanced">("novice");
  const [naturalQuery, setNaturalQuery] = useState("");

  // Advanced Filter States
  const [brand, setBrand] = useState("All");
  const [maxPrice, setMaxPrice] = useState("100000");
  const [minRam, setMinRam] = useState("8");

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (mode === "novice") {
      onSearch("novice", { text: naturalQuery });
    } else {
      onSearch("advanced", { brand, maxPrice, minRam });
    }
  };

  return (
    <div className="relative py-12 px-4 max-w-4xl mx-auto text-center">
      {/* Hero Headline */}
      <motion.h1
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-4xl md:text-6xl font-extrabold tracking-tight mb-4 text-white"
      >
        Find What Fits Your Needs, <br className="hidden sm:block" />
        <span className="bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent">
          Not Just What Matches Your Search.
        </span>
      </motion.h1>
      <p className="text-slate-400 text-base md:text-lg mb-8">
        Grounded in official brand specs, vectorized datasheets, and real-time
        MySQL inventory.
      </p>

      {/* Mode Toggle Switch */}
      <div className="inline-flex p-1 bg-slate-900/90 border border-slate-800 rounded-2xl mb-6">
        <button
          onClick={() => setMode("novice")}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold transition-all duration-300 ${
            mode === "novice"
              ? "bg-purple-600 text-white shadow-lg shadow-purple-600/30"
              : "text-slate-400 hover:text-white"
          }`}
        >
          <Sparkles className="w-4 h-4" />
          Novice (Natural Language AI)
        </button>
        <button
          onClick={() => setMode("advanced")}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold transition-all duration-300 ${
            mode === "advanced"
              ? "bg-purple-600 text-white shadow-lg shadow-purple-600/30"
              : "text-slate-400 hover:text-white"
          }`}
        >
          <SlidersHorizontal className="w-4 h-4" />
          Advanced (Parametric Filters)
        </button>
      </div>

      {/* Search Input Box */}
      <AnimatePresence mode="wait">
        <form onSubmit={handleSearchSubmit}>
          {mode === "novice" ? (
            <motion.div
              key="novice-input"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="relative glass-panel rounded-2xl p-2 flex items-center shadow-2xl border-purple-500/30 focus-within:border-purple-500 transition-all"
            >
              <Search className="w-6 h-6 text-purple-400 ml-3" />
              <input
                type="text"
                value={naturalQuery}
                onChange={(e) => setNaturalQuery(e.target.value)}
                placeholder="e.g., 'I want a laptop under ₹80,000 for 4K video editing and heavy gaming'"
                className="w-full bg-transparent px-4 py-3 text-white placeholder-slate-500 focus:outline-none text-sm md:text-base"
              />
              <button
                type="submit"
                className="bg-purple-600 hover:bg-purple-500 text-white font-medium px-6 py-3 rounded-xl transition-all flex items-center gap-2"
              >
                <span>Search</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </motion.div>
          ) : (
            <motion.div
              key="advanced-input"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="glass-panel rounded-2xl p-6 grid grid-cols-1 md:grid-cols-3 gap-4 text-left border-purple-500/30"
            >
              <div>
                <label className="text-xs text-slate-400 font-semibold mb-2 block">
                  Brand
                </label>
                <select
                  value={brand}
                  onChange={(e) => setBrand(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 text-white rounded-xl py-2.5 px-3 focus:outline-none focus:border-purple-500"
                >
                  <option value="All">All Brands</option>
                  <option value="Asus">Asus</option>
                  <option value="HP">HP</option>
                  <option value="Dell">Dell</option>
                  <option value="Apple">Apple</option>
                </select>
              </div>

              <div>
                <label className="text-xs text-slate-400 font-semibold mb-2 block">
                  Max Price (INR)
                </label>
                <input
                  type="number"
                  value={maxPrice}
                  onChange={(e) => setMaxPrice(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 text-white rounded-xl py-2 px-3 focus:outline-none focus:border-purple-500"
                />
              </div>

              <div>
                <label className="text-xs text-slate-400 font-semibold mb-2 block">
                  Min RAM (GB)
                </label>
                <select
                  value={minRam}
                  onChange={(e) => setMinRam(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 text-white rounded-xl py-2.5 px-3 focus:outline-none focus:border-purple-500"
                >
                  <option value="4">4 GB</option>
                  <option value="8">8 GB</option>
                  <option value="16">16 GB</option>
                  <option value="32">32 GB</option>
                </select>
              </div>

              <div className="md:col-span-3 flex justify-end mt-2">
                <button
                  type="submit"
                  className="bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 text-white font-medium px-6 py-2.5 rounded-xl transition-all flex items-center gap-2"
                >
                  <span>Apply Parametric Filters</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </motion.div>
          )}
        </form>
      </AnimatePresence>

      {/* Quick Prompt Chips */}
      <div className="flex flex-wrap items-center justify-center gap-2 mt-6">
        <span className="text-xs text-slate-500 font-medium">
          Quick Prompts:
        </span>
        {[
          "Laptops under ₹50,000",
          "Dedicated GPU for Video Editing",
          "Long battery life Ultrabooks",
        ].map((chip, idx) => (
          <button
            key={idx}
            onClick={() => {
              setMode("novice");
              setNaturalQuery(chip);
            }}
            className="text-xs px-3 py-1.5 rounded-full bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 transition-all hover:border-purple-500/50"
          >
            {chip}
          </button>
        ))}
      </div>
    </div>
  );
}
