"use client";

import React, { useState, useEffect, useMemo, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Laptop,
  Smartphone,
  Tablet,
  Camera,
  Search,
  SlidersHorizontal,
  Sparkles,
  Cpu,
  Check,
  Plus,
  ArrowRight,
  Heart,
  Star,
  Eye,
  Filter,
  Bell,
  MessageSquarePlus,
  X,
  Zap,
  CheckCircle2,
  Gamepad2,
  Code2,
  Video,
  Briefcase,
  Activity,
  RotateCcw,
  Loader2,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  TrendingUp,
} from "lucide-react";
import { Product } from "../types";
import {
  getProducts,
  getFilterMeta,
  getRecommendations,
  addFavorite,
  removeFavorite,
  submitFeedback,
  RecommendedItem,
} from "../../services/api";
import { getProductImage, formatRamDisplay } from "../../utils/imageHelper";

export { type Product } from "../types";

interface HomeViewProps {
  onCompare: (selectedItems: Product[]) => void;
  shortlisted: Product[];
  setShortlisted: React.Dispatch<React.SetStateAction<Product[]>>;
  wishlist: Product[];
  toggleWishlist: (product: Product) => void;
  onSetPriceAlert?: (product: Product, targetPrice: number) => void;
  onLaunchChatWithQuery?: (query: string) => void;
}

export default function HomeView({
  onCompare,
  shortlisted,
  setShortlisted,
  wishlist,
  toggleWishlist,
  onSetPriceAlert,
  onLaunchChatWithQuery,
}: HomeViewProps) {
  // State for Catalog
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [totalProducts, setTotalProducts] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [availableBrands, setAvailableBrands] = useState<string[]>(["All", "Asus", "HP", "Lenovo", "Dell", "Apple", "Acer", "MSI"]);

  // Search & Filters State
  const [activeCategory, setActiveCategory] = useState("Laptop");
  const [searchMode, setSearchMode] = useState<"novice" | "advanced">("novice");
  const [naturalQuery, setNaturalQuery] = useState("");
  const [brandFilter, setBrandFilter] = useState("All");
  const [maxPrice, setMaxPrice] = useState(150000);
  const [minRam, setMinRam] = useState(0);
  const [sortBy, setSortBy] = useState<"match" | "price-low" | "price-high" | "rating" | "score">("match");
  const [searchKeyword, setSearchKeyword] = useState("");

  // NLP Recommendation State
  const [nlpRecommendations, setNlpRecommendations] = useState<RecommendedItem[]>([]);
  const [isRecommending, setIsRecommending] = useState(false);
  const [nlpSummary, setNlpSummary] = useState<string | null>(null);

  // Usage Profile
  const [usageProfile, setUsageProfile] = useState<"gaming" | "coding" | "editing" | "work">("gaming");

  // Modals & Drawers
  const [fpsModalProduct, setFpsModalProduct] = useState<Product | null>(null);
  const [showQuickMatrixDrawer, setShowQuickMatrixDrawer] = useState(false);
  const [alertProduct, setAlertProduct] = useState<Product | null>(null);
  const [targetPriceInput, setTargetPriceInput] = useState<number>(50000);
  const [alertSuccessMsg, setAlertSuccessMsg] = useState<string | null>(null);
  const [reviewProduct, setReviewProduct] = useState<Product | null>(null);
  const [userRating, setUserRating] = useState<number>(5);
  const [userComment, setUserComment] = useState<string>("");
  const [reviewSubmitted, setReviewSubmitted] = useState<boolean>(false);
  const [quickSummaryProduct, setQuickSummaryProduct] = useState<Product | null>(null);

  const categories = [
    { id: "All", label: "All Products", icon: Sparkles },
    { id: "Laptop", label: "Laptops", icon: Laptop },
    { id: "Phone", label: "Smartphones", icon: Smartphone },
    { id: "Tablet", label: "Tablets", icon: Tablet },
  ];

  const usageOptions = [
    { id: "gaming", label: "Gaming & Esports", desc: "GPU TGP & FPS DLSS 3", icon: Gamepad2 },
    { id: "coding", label: "Software & Dev", desc: "16GB+ RAM & Multi-Core", icon: Code2 },
    { id: "editing", label: "Creator & Video", desc: "OLED 100% DCI-P3 Color", icon: Video },
    { id: "work", label: "Daily Productivity", desc: "10+ Hr Battery & Light", icon: Briefcase },
  ];

  // Fetch filter metadata on mount
  useEffect(() => {
    getFilterMeta()
      .then((meta) => {
        if (meta?.brands?.length) {
          setAvailableBrands(["All", ...meta.brands]);
        }
      })
      .catch(() => {});
  }, []);

  // Fetch products from FastAPI Backend with pagination and filters
  const fetchProductsList = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getProducts({
        search: searchKeyword || undefined,
        category: activeCategory !== "All" ? activeCategory : undefined,
        brand: brandFilter !== "All" ? brandFilter : undefined,
        max_price: maxPrice < 250000 ? maxPrice : undefined,
        min_ram: minRam > 0 ? minRam : undefined,
        sort: sortBy,
        page: currentPage,
        limit: 12,
      });

      setProducts(data.items || []);
      setTotalProducts(data.total || 0);
      setTotalPages(data.pages || 1);
    } catch (err: any) {
      setError(err.message || "Failed to load products from database.");
    } finally {
      setLoading(false);
    }
  }, [searchKeyword, activeCategory, brandFilter, maxPrice, minRam, sortBy, currentPage]);

  useEffect(() => {
    fetchProductsList();
  }, [fetchProductsList]);

  // Handle Natural Language NLP Search
  const handleNaturalSearchSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!naturalQuery.trim()) return;

    setIsRecommending(true);
    setError(null);
    try {
      const res = await getRecommendations(naturalQuery.trim(), activeCategory, 6);
      setNlpRecommendations(res.recommendations || []);
      setNlpSummary(res.summary || `Personalized recommendations generated for "${naturalQuery}"`);
    } catch (err: any) {
      setError("AI Recommendation failed: " + err.message);
    } finally {
      setIsRecommending(false);
    }
  };

  const clearNlpSearch = () => {
    setNlpRecommendations([]);
    setNlpSummary(null);
    setNaturalQuery("");
  };

  const handleToggleShortlist = (prod: Product) => {
    if (shortlisted.some((p) => p.id === prod.id)) {
      setShortlisted(shortlisted.filter((p) => p.id !== prod.id));
    } else {
      if (shortlisted.length >= 4) {
        alert("You can compare up to 4 products at a time.");
        return;
      }
      setShortlisted([...shortlisted, prod]);
    }
  };

  const handleToggleWishlist = async (prod: Product) => {
    const isFav = wishlist.some((p) => p.id === prod.id);
    toggleWishlist(prod);
    try {
      if (isFav) {
        await removeFavorite(prod.id);
      } else {
        await addFavorite(prod.id);
      }
    } catch (err) {
      console.error("Failed to sync favorite with server:", err);
    }
  };

  const handleSavePriceAlert = (e: React.FormEvent) => {
    e.preventDefault();
    if (alertProduct && onSetPriceAlert) {
      onSetPriceAlert(alertProduct, targetPriceInput);
      setAlertSuccessMsg(`Alert active: You will be notified when ${alertProduct.name} drops to ₹${targetPriceInput.toLocaleString()}!`);
      setTimeout(() => {
        setAlertProduct(null);
        setAlertSuccessMsg(null);
      }, 1800);
    }
  };

  const handleSubmitReview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reviewProduct) return;
    try {
      await submitFeedback({
        product_id: reviewProduct.id,
        rating: userRating.toString(),
        reason: userComment,
      });
      setReviewSubmitted(true);
      setTimeout(() => {
        setReviewProduct(null);
        setReviewSubmitted(false);
        setUserComment("");
      }, 1500);
    } catch (err) {
      console.error("Failed to submit review:", err);
    }
  };

  return (
    <div className="py-6 space-y-10 pb-32">
      {/* Category Tabs */}
      <div className="flex items-center justify-between border-b border-slate-200 pb-4 flex-wrap gap-4">
        <div className="flex items-center gap-2 overflow-x-auto pb-2 sm:pb-0">
          {categories.map((cat) => {
            const Icon = cat.icon;
            const isActive = activeCategory === cat.id;
            return (
              <button
                key={cat.id}
                onClick={() => {
                  setActiveCategory(cat.id);
                  setCurrentPage(1);
                }}
                className={`flex items-center gap-2.5 px-5 py-2.5 rounded-2xl font-extrabold text-xs transition-all cursor-pointer ${
                  isActive
                    ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-md shadow-blue-500/25"
                    : "bg-white text-slate-600 hover:text-slate-900 border border-slate-200/90 hover:bg-slate-50"
                }`}
              >
                <Icon className="w-4 h-4" />
                {cat.label}
              </button>
            );
          })}
        </div>

        {/* Live Inventory Counter */}
        <div className="flex items-center gap-2 text-xs font-bold text-slate-500 bg-white px-3.5 py-2 rounded-xl border border-slate-200">
          <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
          <span>{totalProducts > 0 ? `${totalProducts.toLocaleString()} Verified Products in MySQL` : "Connecting to Database..."}</span>
        </div>
      </div>

      {/* Hero Search Section */}
      <div className="relative bg-gradient-to-br from-slate-950 via-[#0B132B] to-[#1C2541] rounded-3xl p-6 sm:p-10 text-white overflow-hidden shadow-2xl border border-indigo-900/40">
        <div className="absolute top-0 right-0 w-96 h-96 bg-blue-500/20 blur-[120px] rounded-full pointer-events-none" />
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-indigo-500/20 blur-[120px] rounded-full pointer-events-none" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-blue-900/20 via-transparent to-transparent pointer-events-none" />

        <div className="max-w-3xl mx-auto text-center space-y-6 relative z-10">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-blue-500/10 backdrop-blur-md border border-blue-400/30 text-blue-300 text-xs font-black shadow-sm">
            <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
            AI Specification & Recommendation Engine
          </div>

          <h1 className="text-3xl sm:text-5xl font-black tracking-tight leading-tight text-white drop-shadow-md">
            <span className="text-white drop-shadow-sm">Find the Perfect Hardware with</span> <br />
            <span className="bg-gradient-to-r from-cyan-300 via-blue-400 to-indigo-300 bg-clip-text text-transparent font-black">
              Zero Spec Hallucinations
            </span>
          </h1>

          <p className="text-slate-200 text-sm sm:text-base font-medium max-w-xl mx-auto drop-shadow-xs">
            Grounded strictly in verified OEM datasheets, benchmarked thermals, and live MySQL catalog specs.
          </p>

          {/* Mode Switcher */}
          <div className="inline-flex p-1 bg-slate-900/90 border border-slate-700/80 rounded-2xl shadow-inner">
            <button
              onClick={() => setSearchMode("novice")}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-black transition-all cursor-pointer ${
                searchMode === "novice"
                  ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg shadow-blue-500/30"
                  : "text-slate-300 hover:text-white"
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              Natural Language AI Search
            </button>
            <button
              onClick={() => setSearchMode("advanced")}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-black transition-all cursor-pointer ${
                searchMode === "advanced"
                  ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg shadow-blue-500/30"
                  : "text-slate-300 hover:text-white"
              }`}
            >
              <SlidersHorizontal className="w-3.5 h-3.5" />
              Parametric Keyword Filters
            </button>
          </div>

          {/* Search Inputs */}
          {searchMode === "novice" ? (
            <form onSubmit={handleNaturalSearchSubmit} className="relative">
              <div className="relative bg-slate-900/90 backdrop-blur-xl rounded-2xl p-2 flex items-center border border-slate-700/90 shadow-2xl focus-within:border-blue-400 focus-within:ring-2 focus-within:ring-blue-400/20 transition-all">
                <Search className="w-5 h-5 text-cyan-400 ml-3 shrink-0" />
                <input
                  type="text"
                  value={naturalQuery}
                  onChange={(e) => setNaturalQuery(e.target.value)}
                  placeholder="e.g. 'I need a laptop under ₹80,000 for gaming with 16GB RAM' or 'lightweight for coding'"
                  className="w-full bg-transparent px-4 py-3 text-white font-medium placeholder-slate-400 focus:outline-none text-xs sm:text-sm"
                />
                <button
                  type="submit"
                  disabled={isRecommending}
                  className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-black px-6 py-3 rounded-xl text-xs transition-all flex items-center gap-2 shrink-0 cursor-pointer disabled:opacity-50 shadow-md shadow-blue-500/25"
                >
                  {isRecommending ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Analyzing...
                    </>
                  ) : (
                    <>
                      <span>Ask AI</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>

              {/* Quick Prompt Chips */}
              <div className="flex flex-wrap items-center justify-center gap-2 mt-4">
                <span className="text-[11px] text-slate-300 font-bold">Quick Prompts:</span>
                {[
                  "Gaming laptop under ₹80,000 with RTX GPU",
                  "Laptop under ₹50,000 for coding & college",
                  "Creator machine with OLED display under 70k",
                  "MacBook or ultrabook with best battery life",
                ].map((chip, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => {
                      setNaturalQuery(chip);
                    }}
                    className="text-[11px] font-semibold px-3.5 py-1.5 rounded-full bg-slate-800/90 hover:bg-blue-600/30 border border-slate-700 hover:border-blue-400 text-slate-200 hover:text-white transition-all cursor-pointer shadow-2xs"
                  >
                    {chip}
                  </button>
                ))}
              </div>
            </form>
          ) : (
            <div className="bg-white/10 backdrop-blur-xl rounded-2xl p-4 sm:p-6 border border-white/20 text-left space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="text-[11px] font-bold text-slate-300 block mb-1.5">Brand</label>
                  <select
                    value={brandFilter}
                    onChange={(e) => {
                      setBrandFilter(e.target.value);
                      setCurrentPage(1);
                    }}
                    className="w-full bg-slate-900/90 border border-slate-700 text-white rounded-xl py-2.5 px-3 text-xs font-semibold focus:outline-none focus:border-blue-400"
                  >
                    {availableBrands.map((b) => (
                      <option key={b} value={b} className="bg-slate-900 text-white">
                        {b === "All" ? "All Brands" : b}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-[11px] font-bold text-slate-300 block mb-1.5">
                    Max Price: ₹{maxPrice.toLocaleString()}
                  </label>
                  <input
                    type="range"
                    min={20000}
                    max={250000}
                    step={5000}
                    value={maxPrice}
                    onChange={(e) => {
                      setMaxPrice(Number(e.target.value));
                      setCurrentPage(1);
                    }}
                    className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                  />
                </div>

                <div>
                  <label className="text-[11px] font-bold text-slate-300 block mb-1.5">Min RAM</label>
                  <select
                    value={minRam}
                    onChange={(e) => {
                      setMinRam(Number(e.target.value));
                      setCurrentPage(1);
                    }}
                    className="w-full bg-slate-900/90 border border-slate-700 text-white rounded-xl py-2.5 px-3 text-xs font-semibold focus:outline-none focus:border-blue-400"
                  >
                    <option value={0}>Any RAM</option>
                    <option value={8}>8 GB+</option>
                    <option value={16}>16 GB+</option>
                    <option value={24}>24 GB+</option>
                    <option value={32}>32 GB+</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-white/10 flex-wrap gap-2">
                <input
                  type="text"
                  value={searchKeyword}
                  onChange={(e) => {
                    setSearchKeyword(e.target.value);
                    setCurrentPage(1);
                  }}
                  placeholder="Keyword search (e.g. i7, RTX 4060, Vivobook)..."
                  className="bg-slate-900/90 border border-slate-700 text-white rounded-xl py-2 px-3 text-xs w-full sm:w-72 focus:outline-none focus:border-blue-400"
                />

                <button
                  onClick={() => {
                    setBrandFilter("All");
                    setMaxPrice(250000);
                    setMinRam(0);
                    setSearchKeyword("");
                    setCurrentPage(1);
                  }}
                  className="text-xs font-bold text-slate-400 hover:text-white flex items-center gap-1 cursor-pointer"
                >
                  <RotateCcw className="w-3.5 h-3.5" /> Reset Filters
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* NLP AI Recommendations Section (Rendered when AI query is active) */}
      <AnimatePresence>
        {nlpRecommendations.length > 0 && (
          <motion.section
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="bg-blue-50/70 border border-blue-200 rounded-3xl p-6 sm:p-8 space-y-6"
          >
            <div className="flex items-start sm:items-center justify-between gap-4 flex-col sm:flex-row">
              <div>
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-600 text-white text-[11px] font-black uppercase tracking-wider mb-2">
                  <Sparkles className="w-3.5 h-3.5" /> AI Recommendation Engine Results
                </div>
                <h2 className="text-2xl font-black text-slate-900 tracking-tight">
                  Personalized Spec Matches
                </h2>
                {nlpSummary && (
                  <p className="text-slate-600 text-xs sm:text-sm font-semibold mt-1">
                    {nlpSummary}
                  </p>
                )}
              </div>

              <button
                onClick={clearNlpSearch}
                className="px-4 py-2 bg-white hover:bg-slate-100 border border-slate-300 text-slate-700 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer"
              >
                <X className="w-4 h-4" /> Clear AI Results
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {nlpRecommendations.map((item, idx) => {
                const prod = item.product;
                const isShortlisted = shortlisted.some((p) => p.id === prod.id);
                const isFav = wishlist.some((p) => p.id === prod.id);

                return (
                  <motion.div
                    key={prod.id}
                    initial={{ opacity: 0, y: 15 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.05 }}
                    className="bg-white border-2 border-blue-300/80 rounded-3xl p-5 flex flex-col justify-between shadow-lg shadow-blue-500/5 hover:shadow-xl transition-all"
                  >
                    <div>
                      {/* Top Rank Badge & Match Score */}
                      <div className="flex items-center justify-between mb-3">
                        <span className="px-2.5 py-1 rounded-lg bg-blue-600 text-white text-xs font-black">
                          #{item.rank} Top Pick
                        </span>
                        <div className="flex items-center gap-1 text-xs font-black text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-lg border border-emerald-200">
                          <Zap className="w-3.5 h-3.5 fill-emerald-600" />
                          {item.match_score}% Match
                        </div>
                      </div>

                      {/* Product Image */}
                      <div className="h-44 w-full rounded-2xl overflow-hidden mb-4 bg-slate-100 relative group">
                        <img
                          src={prod.image}
                          alt={prod.name}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                        />
                        <button
                          onClick={() => handleToggleWishlist(prod)}
                          className="absolute top-3 right-3 p-2 bg-white/90 backdrop-blur-md rounded-xl shadow-md text-slate-700 hover:text-rose-500 transition-colors cursor-pointer"
                        >
                          <Heart className={`w-4 h-4 ${isFav ? "fill-rose-500 text-rose-500" : ""}`} />
                        </button>
                      </div>

                      {/* Title & Price */}
                      <div className="text-[11px] font-extrabold text-blue-600 uppercase tracking-wider">
                        {prod.brand}
                      </div>
                      <h3 className="font-extrabold text-base text-slate-900 tracking-tight line-clamp-1">
                        {prod.name}
                      </h3>
                      <div className="text-xl font-black text-slate-900 mt-1">
                        ₹{prod.price.toLocaleString()}
                      </div>

                      {/* AI Justification Box */}
                      <div className="mt-3 p-3 bg-blue-50/70 border border-blue-200 rounded-xl text-xs font-medium text-slate-700 space-y-1.5">
                        <p className="font-bold text-blue-950 flex items-center gap-1">
                          <Sparkles className="w-3.5 h-3.5 text-blue-600" /> Why this matches:
                        </p>
                        <p className="text-[11px] leading-relaxed">{item.reason}</p>
                      </div>

                      {/* Hardware Specs Grid */}
                      <div className="grid grid-cols-2 gap-2 mt-3 text-xs font-semibold text-slate-700">
                        <div className="p-2 bg-slate-50 border border-slate-200 rounded-xl flex items-center gap-1.5">
                          <Cpu className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                          <span className="truncate">{prod.cpu}</span>
                        </div>
                        <div className="p-2 bg-slate-50 border border-slate-200 rounded-xl flex items-center gap-1.5">
                          <Activity className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                          <span className="truncate">{Math.round(prod.ram)}GB RAM</span>
                        </div>
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex items-center gap-2 mt-4 pt-4 border-t border-slate-100">
                      <button
                        onClick={() => handleToggleShortlist(prod)}
                        className={`flex-1 py-2.5 rounded-xl font-bold text-xs flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
                          isShortlisted
                            ? "bg-emerald-600 text-white"
                            : "bg-blue-600 hover:bg-blue-700 text-white shadow-md shadow-blue-500/20"
                        }`}
                      >
                        {isShortlisted ? (
                          <>
                            <Check className="w-4 h-4" /> Added to Compare
                          </>
                        ) : (
                          <>
                            <Plus className="w-4 h-4" /> Compare Spec
                          </>
                        )}
                      </button>

                      {prod.fpsData && prod.fpsData.length > 0 && (
                        <button
                          onClick={() => setFpsModalProduct(prod)}
                          className="p-2.5 bg-slate-100 hover:bg-slate-200 text-slate-800 rounded-xl transition-colors cursor-pointer"
                          title="View Gaming FPS Benchmarks"
                        >
                          <Gamepad2 className="w-4 h-4 text-indigo-600" />
                        </button>
                      )}
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </motion.section>
        )}
      </AnimatePresence>

      {/* Catalog Header & Sort Options */}
      <div className="flex items-center justify-between flex-wrap gap-4 border-b border-slate-200 pb-4">
        <div>
          <h2 className="text-2xl font-black text-slate-900 tracking-tight flex items-center gap-2">
            Verified Product Catalog
          </h2>
          <p className="text-slate-500 text-xs font-semibold mt-0.5">
            Showing {products.length} of {totalProducts.toLocaleString()} items
          </p>
        </div>

        <div className="flex items-center gap-3">
          <label className="text-xs font-bold text-slate-500">Sort by:</label>
          <select
            value={sortBy}
            onChange={(e) => {
              setSortBy(e.target.value as any);
              setCurrentPage(1);
            }}
            className="bg-white border border-slate-200 text-slate-800 rounded-xl px-3 py-1.5 text-xs font-bold focus:outline-none focus:border-blue-500"
          >
            <option value="match">AI Recommendation Score</option>
            <option value="price-low">Price: Low to High</option>
            <option value="price-high">Price: High to Low</option>
            <option value="rating">Highest User Rating</option>
            <option value="score">Hardware Benchmark</option>
          </select>
        </div>
      </div>

      {/* Main Products Grid */}
      {loading ? (
        <div className="py-24 text-center space-y-4">
          <Loader2 className="w-10 h-10 text-blue-600 animate-spin mx-auto" />
          <p className="text-sm font-bold text-slate-600">Loading catalog from database...</p>
        </div>
      ) : error ? (
        <div className="py-16 text-center space-y-4 bg-rose-50 border border-rose-200 rounded-3xl p-8 max-w-lg mx-auto">
          <AlertCircle className="w-10 h-10 text-rose-600 mx-auto" />
          <h3 className="text-lg font-black text-rose-900">Unable to load products</h3>
          <p className="text-xs font-medium text-rose-700">{error}</p>
          <button
            onClick={fetchProductsList}
            className="px-6 py-2.5 bg-rose-600 text-white rounded-xl text-xs font-black shadow-md hover:bg-rose-700 transition-all cursor-pointer"
          >
            Try Again
          </button>
        </div>
      ) : products.length === 0 ? (
        <div className="py-20 text-center space-y-3 bg-white border border-slate-200 rounded-3xl p-8">
          <Filter className="w-10 h-10 text-slate-400 mx-auto" />
          <h3 className="text-lg font-black text-slate-900">No products match your filters</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            Try adjusting your budget slider, choosing another brand, or clearing search keywords.
          </p>
          <button
            onClick={() => {
              setBrandFilter("All");
              setMaxPrice(250000);
              setMinRam(0);
              setSearchKeyword("");
            }}
            className="mt-2 px-5 py-2 bg-blue-600 text-white rounded-xl text-xs font-bold cursor-pointer"
          >
            Reset Filters
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {products.map((prod, idx) => {
            const isShortlisted = shortlisted.some((p) => p.id === prod.id);
            const isFav = wishlist.some((p) => p.id === prod.id);

            return (
              <motion.div
                key={prod.id}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: (idx % 12) * 0.03 }}
                className="bg-white border border-slate-200/90 rounded-3xl p-5 flex flex-col justify-between shadow-2xs hover:shadow-xl hover:border-blue-300 transition-all group"
              >
                <div>
                  {/* Brand & Badges */}
                  <div className="flex items-center justify-between mb-2.5">
                    <span className="text-[11px] font-black text-blue-600 uppercase tracking-wider">
                      {prod.brand}
                    </span>
                    {prod.badge && (
                      <span className="text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                        {prod.badge}
                      </span>
                    )}
                  </div>

                  {/* Product Image */}
                  <div className="h-44 w-full rounded-2xl overflow-hidden mb-3.5 bg-slate-100 relative">
                    <img
                      src={getProductImage(prod)}
                      alt={prod.name}
                      onError={(e) => {
                        (e.target as HTMLImageElement).src = getProductImage({ category: prod.category });
                      }}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                    />
                    <button
                      onClick={() => handleToggleWishlist(prod)}
                      className="absolute top-2.5 right-2.5 p-2 bg-white/90 backdrop-blur-md rounded-xl shadow-md text-slate-700 hover:text-rose-500 transition-colors cursor-pointer"
                    >
                      <Heart className={`w-4 h-4 ${isFav ? "fill-rose-500 text-rose-500" : ""}`} />
                    </button>
                  </div>

                  {/* Title & Price */}
                  <h3 className="font-extrabold text-sm text-slate-900 tracking-tight line-clamp-1 group-hover:text-blue-600 transition-colors">
                    {prod.name}
                  </h3>
                  <div className="flex items-baseline gap-2 mt-1">
                    <span className="text-lg font-black text-slate-900">
                      ₹{prod.price.toLocaleString()}
                    </span>
                    {prod.original_price && prod.original_price > prod.price && (
                      <span className="text-xs text-slate-400 line-through font-semibold">
                        ₹{prod.original_price.toLocaleString()}
                      </span>
                    )}
                  </div>

                  {/* Rating & Benchmark Score */}
                  <div className="flex items-center justify-between mt-2.5 text-xs font-bold">
                    <div className="flex items-center gap-1 text-amber-500">
                      <Star className="w-3.5 h-3.5 fill-amber-400" />
                      <span>{prod.rating || 4.2}</span>
                      <span className="text-slate-400 text-[10px]">({prod.reviews || 20})</span>
                    </div>

                    <div className="flex items-center gap-1 text-blue-600 bg-blue-50 px-2 py-0.5 rounded-md">
                      <Activity className="w-3 h-3" />
                      <span className="text-[11px]">{prod.score}/100</span>
                    </div>
                  </div>

                  {/* Hardware Chips */}
                  <div className="grid grid-cols-2 gap-1.5 mt-3 text-[11px] font-semibold text-slate-700">
                    <div className="p-1.5 bg-slate-50 border border-slate-200/80 rounded-lg truncate">
                      {prod.cpu}
                    </div>
                    <div className="p-1.5 bg-slate-50 border border-slate-200/80 rounded-lg truncate">
                      {formatRamDisplay(prod.ram)}
                    </div>
                  </div>
                </div>

                {/* Bottom Action Bar */}
                <div className="flex items-center gap-2 mt-4 pt-3.5 border-t border-slate-100">
                  <button
                    onClick={() => handleToggleShortlist(prod)}
                    className={`flex-1 py-2.5 rounded-xl font-bold text-xs flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
                      isShortlisted
                        ? "bg-emerald-600 text-white"
                        : "bg-slate-100 hover:bg-slate-200/80 text-slate-800"
                    }`}
                  >
                    {isShortlisted ? (
                      <>
                        <Check className="w-3.5 h-3.5" /> Shortlisted
                      </>
                    ) : (
                      <>
                        <Plus className="w-3.5 h-3.5" /> Compare
                      </>
                    )}
                  </button>

                  <button
                    onClick={() => {
                      setAlertProduct(prod);
                      setTargetPriceInput(Math.round(prod.price * 0.95));
                    }}
                    className="p-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl transition-colors cursor-pointer"
                    title="Set Price Drop Alert"
                  >
                    <Bell className="w-3.5 h-3.5" />
                  </button>

                  <button
                    onClick={() => setReviewProduct(prod)}
                    className="p-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl transition-colors cursor-pointer"
                    title="Submit Rating / Review"
                  >
                    <MessageSquarePlus className="w-3.5 h-3.5" />
                  </button>
                </div>
              </motion.div>
            );
          })}
        </div>
      )}

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-3 pt-6">
          <button
            onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
            disabled={currentPage === 1}
            className="p-2.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer text-slate-700"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>

          <span className="text-xs font-bold text-slate-700 bg-white px-4 py-2 rounded-xl border border-slate-200">
            Page {currentPage} of {totalPages}
          </span>

          <button
            onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
            disabled={currentPage === totalPages}
            className="p-2.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer text-slate-700"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Floating Comparison Sticky Dock */}
      <AnimatePresence>
        {shortlisted.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 50, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 50, scale: 0.95 }}
            className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 bg-slate-950/95 backdrop-blur-2xl border border-slate-700/80 rounded-2xl p-3 sm:p-3.5 shadow-2xl shadow-blue-950/60 flex items-center gap-3 sm:gap-4 text-white max-w-2xl w-[94%]"
          >
            <div className="flex items-center gap-2 overflow-x-auto flex-1 py-0.5 scrollbar-none">
              {shortlisted.map((item) => {
                const displayName = item.name.toLowerCase().startsWith(item.brand.toLowerCase() + " ")
                  ? item.name
                  : `${item.brand} ${item.name}`;

                return (
                  <div
                    key={item.id}
                    className="flex items-center gap-2 bg-slate-800/90 border border-slate-700 hover:border-slate-600 px-3 py-1.5 rounded-xl shrink-0 text-xs font-bold text-slate-100 shadow-2xs"
                  >
                    <span className="truncate max-w-[130px]">{displayName}</span>
                    <button
                      onClick={() => handleToggleShortlist(item)}
                      className="text-slate-400 hover:text-rose-400 p-0.5 rounded cursor-pointer transition-colors"
                      title="Remove from comparison"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                );
              })}
            </div>

            <div className="flex items-center gap-2 shrink-0 border-l border-slate-800 pl-3">
              <button
                onClick={() => setShortlisted([])}
                className="text-xs font-bold text-slate-400 hover:text-rose-400 px-2 py-1.5 rounded-lg hover:bg-slate-900 transition-colors cursor-pointer"
              >
                Clear
              </button>
              <button
                onClick={() => onCompare(shortlisted)}
                className="px-5 py-2.5 bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white rounded-xl text-xs font-black shadow-lg shadow-blue-500/30 flex items-center gap-1.5 cursor-pointer transition-all hover:scale-[1.02]"
              >
                <span>Compare Matrix ({shortlisted.length})</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Price Drop Alert Modal */}
      <AnimatePresence>
        {alertProduct && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-white rounded-3xl p-6 max-w-md w-full shadow-2xl border border-slate-200"
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-extrabold text-lg text-slate-900 flex items-center gap-2">
                  <Bell className="w-5 h-5 text-blue-600" /> Set Price Alert
                </h3>
                <button onClick={() => setAlertProduct(null)} className="text-slate-400 hover:text-slate-700">
                  <X className="w-5 h-5" />
                </button>
              </div>

              {alertSuccessMsg ? (
                <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-2xl text-xs font-bold text-emerald-800 flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                  {alertSuccessMsg}
                </div>
              ) : (
                <form onSubmit={handleSavePriceAlert} className="space-y-4">
                  <p className="text-xs text-slate-600">
                    We&apos;ll notify you when <strong>{alertProduct.name}</strong> drops below your target price.
                  </p>
                  <div>
                    <label className="text-xs font-bold text-slate-500 block mb-1">Target Price (INR)</label>
                    <input
                      type="number"
                      value={targetPriceInput}
                      onChange={(e) => setTargetPriceInput(Number(e.target.value))}
                      className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm font-bold text-slate-900 focus:outline-none focus:border-blue-500"
                    />
                  </div>
                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setAlertProduct(null)}
                      className="px-4 py-2 text-xs font-bold text-slate-600 hover:bg-slate-100 rounded-xl"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-xl shadow-md"
                    >
                      Activate Tracker
                    </button>
                  </div>
                </form>
              )}
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Review / Feedback Modal */}
      <AnimatePresence>
        {reviewProduct && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-white rounded-3xl p-6 max-w-md w-full shadow-2xl border border-slate-200"
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-extrabold text-lg text-slate-900 flex items-center gap-2">
                  <MessageSquarePlus className="w-5 h-5 text-blue-600" /> Review {reviewProduct.brand} {reviewProduct.name}
                </h3>
                <button onClick={() => setReviewProduct(null)} className="text-slate-400 hover:text-slate-700">
                  <X className="w-5 h-5" />
                </button>
              </div>

              {reviewSubmitted ? (
                <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-2xl text-xs font-bold text-emerald-800 flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                  Thank you! Your feedback has been stored in MySQL.
                </div>
              ) : (
                <form onSubmit={handleSubmitReview} className="space-y-4">
                  <div>
                    <label className="text-xs font-bold text-slate-500 block mb-1">Rating</label>
                    <div className="flex items-center gap-2">
                      {[1, 2, 3, 4, 5].map((star) => (
                        <button
                          key={star}
                          type="button"
                          onClick={() => setUserRating(star)}
                          className="p-1 cursor-pointer"
                        >
                          <Star
                            className={`w-6 h-6 ${
                              star <= userRating ? "fill-amber-400 text-amber-400" : "text-slate-300"
                            }`}
                          />
                        </button>
                      ))}
                    </div>
                  </div>

                  <div>
                    <label className="text-xs font-bold text-slate-500 block mb-1">Comments / Reason</label>
                    <textarea
                      rows={3}
                      value={userComment}
                      onChange={(e) => setUserComment(e.target.value)}
                      placeholder="Share your experience with build quality, battery, or thermals..."
                      className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 text-xs font-medium text-slate-900 focus:outline-none focus:border-blue-500"
                    />
                  </div>

                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setReviewProduct(null)}
                      className="px-4 py-2 text-xs font-bold text-slate-600 hover:bg-slate-100 rounded-xl"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-xl shadow-md"
                    >
                      Submit Review
                    </button>
                  </div>
                </form>
              )}
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* FPS Benchmarks Modal */}
      <AnimatePresence>
        {fpsModalProduct && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-white rounded-3xl p-6 max-w-lg w-full shadow-2xl border border-slate-200"
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-extrabold text-lg text-slate-900 flex items-center gap-2">
                  <Gamepad2 className="w-5 h-5 text-indigo-600" /> Gaming Benchmarks: {fpsModalProduct.brand} {fpsModalProduct.name}
                </h3>
                <button onClick={() => setFpsModalProduct(null)} className="text-slate-400 hover:text-slate-700">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="space-y-3 mb-6">
                {(fpsModalProduct.fpsData || []).map((fps, i) => (
                  <div key={i} className="flex items-center justify-between p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs">
                    <div>
                      <span className="font-bold text-slate-900">{fps.game}</span>
                      <span className="text-slate-500 ml-2">({fps.resolution})</span>
                    </div>
                    <span className="font-black text-indigo-600 bg-indigo-50 px-2.5 py-1 rounded-lg">
                      {fps.fps} FPS
                    </span>
                  </div>
                ))}
              </div>

              <div className="flex justify-end">
                <button
                  onClick={() => setFpsModalProduct(null)}
                  className="px-5 py-2 bg-slate-900 text-white rounded-xl text-xs font-bold"
                >
                  Close Benchmarks
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
