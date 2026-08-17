"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sparkles,
  User as UserIcon,
  Settings,
  Bell,
  Check,
  Lock,
  Eye,
  EyeOff,
  History,
  Trash2,
  BarChart3,
  TrendingUp,
  Activity,
  Layers,
  Heart,
  Scale,
  RefreshCw,
  Loader2,
  CheckCircle2,
  Search,
  Upload,
  ArrowRight,
  Sliders,
  ExternalLink,
  Shield,
  FileText,
  Camera,
  Star,
  Cpu,
  Compass,
  Zap,
  MessageSquare,
  Clock,
} from "lucide-react";
import { UserProfile, UserPreferences, Product } from "../types";
import {
  getProfile,
  updateProfile,
  uploadProfileImage,
  removeProfileImage,
  changeAccountPassword,
  getPreferences,
  updatePreferences,
  getUserConversations,
  deleteUserConversation,
  UserConversationSummary,
  getUserSavedComparisons,
  deleteUserSavedComparison,
  SavedComparisonItem,
  getDashboardStats,
  getCategoryDistribution,
  getPriceSegmentation,
  getBrandMarketShare,
  getPersonalizedRecommendations,
  getFavorites,
  addFavorite,
  removeFavorite,
  getHistory,
  deleteHistoryItem,
  clearAllHistory,
  getAssetUrl,
  DashboardStats,
  CategoryDistributionItem,
  PriceSegmentItem,
  BrandShareItem,
  RecommendedItem,
} from "../../services/api";

import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  PieChart,
  Pie,
  Cell,
} from "recharts";

interface DashboardViewProps {
  user: UserProfile | null;
  notifications: string[];
  initialTab?: string;
  onNavigate?: (view: string, query?: string) => void;
  onUpdateUser?: (updated: UserProfile) => void;
}

const BRAND_COLORS = ["#2563EB", "#06B6D4", "#6366F1", "#10B981", "#F59E0B", "#EC4899", "#8B5CF6"];

export default function DashboardView({
  user,
  notifications,
  initialTab = "overview",
  onNavigate,
  onUpdateUser,
}: DashboardViewProps) {
  const [activeTab, setActiveTab] = useState<"overview" | "profile" | "conversations" | "comparisons" | "history">(
    (initialTab as any) || "overview"
  );

  // Profile Form State
  const [name, setName] = useState(user?.name || "");
  const [email, setEmail] = useState(user?.email || "");
  const [title, setTitle] = useState(user?.title || "");
  const [phone, setPhone] = useState(user?.phone || "");
  const [location, setLocation] = useState(user?.location || "");
  const [bio, setBio] = useState(user?.bio || "");
  const [avatar, setAvatar] = useState(user?.avatar || "");
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null);
  const [isUploadingPhoto, setIsUploadingPhoto] = useState(false);

  // Password Change State
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  // Preferences Form State
  const [preferences, setPreferences] = useState<UserPreferences>(
    user?.preferences || {
      defaultCategory: "Laptop",
      aiStyle: "performance",
      currency: "INR",
      notificationsEmail: true,
      notificationsPriceDrops: true,
      darkMode: false,
      budgetMin: 30000,
      budgetMax: 120000,
      priorityFeatures: ["High Performance", "OLED Display"],
    }
  );

  // Real Database Analytics & Personalized Recs State
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [categoryDistribution, setCategoryDistribution] = useState<CategoryDistributionItem[]>([]);
  const [priceSegmentation, setPriceSegmentation] = useState<PriceSegmentItem[]>([]);
  const [brandMarketShare, setBrandMarketShare] = useState<BrandShareItem[]>([]);
  const [personalizedRecs, setPersonalizedRecs] = useState<RecommendedItem[]>([]);
  const [searchHistory, setSearchHistory] = useState<any[]>([]);
  const [wishlistItems, setWishlistItems] = useState<Product[]>([]);
  const [userConversations, setUserConversations] = useState<UserConversationSummary[]>([]);
  const [savedComparisons, setSavedComparisons] = useState<SavedComparisonItem[]>([]);
  const [isLoadingDashboard, setIsLoadingDashboard] = useState(true);

  // AI Prompt Box State
  const [aiSearchPrompt, setAiSearchPrompt] = useState("");

  // Feedback Messages
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState<string | null>(null);
  const [saveErrorMsg, setSaveErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (initialTab && ["overview", "profile", "conversations", "comparisons", "history"].includes(initialTab)) {
      setActiveTab(initialTab as any);
    }
  }, [initialTab]);

  useEffect(() => {
    loadAllDashboardData();
  }, []);

  const loadAllDashboardData = async () => {
    setIsLoadingDashboard(true);
    try {
      const [
        profileData,
        prefsData,
        statsData,
        catData,
        priceData,
        brandData,
        recsData,
        historyData,
        favsData,
        conversationsData,
        comparisonsData,
      ] = await Promise.all([
        getProfile().catch(() => null),
        getPreferences().catch(() => null),
        getDashboardStats().catch(() => null),
        getCategoryDistribution().catch(() => []),
        getPriceSegmentation().catch(() => []),
        getBrandMarketShare().catch(() => []),
        getPersonalizedRecommendations().catch(() => null),
        getHistory().catch(() => ({ searches: [], comparisons: [] })),
        getFavorites().catch(() => ({ items: [], total: 0 })),
        getUserConversations().catch(() => []),
        getUserSavedComparisons().catch(() => []),
      ]);

      if (profileData) {
        setName(profileData.name || "");
        setEmail(profileData.email || "");
        setTitle(profileData.title || "");
        setPhone(profileData.phone || "");
        setLocation(profileData.location || "");
        setBio(profileData.bio || "");
        setAvatar(profileData.avatar || "");
        if (onUpdateUser) onUpdateUser(profileData);
      }

      if (prefsData) {
        setPreferences(prefsData);
      }

      if (statsData) {
        setStats(statsData);
      }

      if (catData && catData.length > 0) {
        setCategoryDistribution(catData);
      }

      if (priceData && priceData.length > 0) {
        setPriceSegmentation(priceData);
      }

      if (brandData && brandData.length > 0) {
        setBrandMarketShare(brandData);
      }

      if (recsData?.recommendations) {
        setPersonalizedRecs(recsData.recommendations);
      }

      if (historyData) {
        setSearchHistory(historyData.searches || []);
      }

      if (favsData?.items) {
        setWishlistItems(favsData.items);
      }

      if (Array.isArray(conversationsData)) {
        setUserConversations(conversationsData);
      }

      if (Array.isArray(comparisonsData)) {
        setSavedComparisons(comparisonsData);
      }
    } catch (err) {
      console.error("Error loading dashboard data:", err);
    } finally {
      setIsLoadingDashboard(false);
    }
  };

  // Profile Image Upload Handler
  const handlePhotoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Client-side preview
    const previewUrl = URL.createObjectURL(file);
    setAvatarPreview(previewUrl);
    setIsUploadingPhoto(true);
    setSaveSuccessMsg(null);
    setSaveErrorMsg(null);

    try {
      const updatedUser = await uploadProfileImage(file);
      setAvatar(updatedUser.avatar || "");
      if (onUpdateUser) onUpdateUser(updatedUser);
      setSaveSuccessMsg("Profile photo updated and saved to database!");
      setTimeout(() => setSaveSuccessMsg(null), 3000);
    } catch (err: any) {
      setSaveErrorMsg(err.message || "Failed to upload profile photo.");
      setAvatarPreview(null);
    } finally {
      setIsUploadingPhoto(false);
    }
  };

  const handleRemovePhoto = async () => {
    setIsUploadingPhoto(true);
    try {
      const updatedUser = await removeProfileImage();
      setAvatar(updatedUser.avatar || "");
      setAvatarPreview(null);
      if (onUpdateUser) onUpdateUser(updatedUser);
      setSaveSuccessMsg("Profile photo reset to default.");
      setTimeout(() => setSaveSuccessMsg(null), 3000);
    } catch (err: any) {
      setSaveErrorMsg(err.message || "Failed to remove photo.");
    } finally {
      setIsUploadingPhoto(false);
    }
  };

  // Save Profile Details
  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setSaveSuccessMsg(null);
    setSaveErrorMsg(null);

    try {
      // Validate passwords if changing or setting password
      if (newPassword) {
        const isGoogleOnly = user?.authMethod === "google" || user?.authMethod === "Google";
        if (!currentPassword && !isGoogleOnly) {
          throw new Error("Please enter your current password to set a new password.");
        }
        if (newPassword !== confirmPassword) {
          throw new Error("New password and confirm password do not match.");
        }
        if (newPassword.length < 6) {
          throw new Error("New password must be at least 6 characters long.");
        }
      }

      const updated = await updateProfile({
        name: name.trim(),
        title: title.trim(),
        phone: phone.trim(),
        location: location.trim(),
        bio: bio.trim(),
        currentPassword: currentPassword || undefined,
        newPassword: newPassword || undefined,
      });

      if (onUpdateUser) onUpdateUser(updated);
      setSaveSuccessMsg("Profile details and security settings updated successfully!");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setTimeout(() => setSaveSuccessMsg(null), 3000);
    } catch (err: any) {
      setSaveErrorMsg(err.message || "Failed to update profile.");
    } finally {
      setIsSaving(false);
    }
  };

  // Save Preferences
  const handleSavePreferences = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setSaveSuccessMsg(null);
    setSaveErrorMsg(null);

    try {
      const updated = await updatePreferences(preferences);
      setPreferences(updated);
      setSaveSuccessMsg("Personalization & search preferences saved to database!");
      setTimeout(() => setSaveSuccessMsg(null), 3000);
    } catch (err: any) {
      setSaveErrorMsg(err.message || "Failed to update preferences.");
    } finally {
      setIsSaving(false);
    }
  };

  // Delete Individual Conversation
  const handleDeleteConversation = async (cid: string) => {
    try {
      await deleteUserConversation(cid);
      setUserConversations((prev) => prev.filter((c) => c.conversation_id !== cid));
    } catch (err) {
      console.error("Failed to delete conversation:", err);
    }
  };

  // Delete Individual Saved Comparison
  const handleDeleteSavedComparison = async (cid: string) => {
    try {
      await deleteUserSavedComparison(cid);
      setSavedComparisons((prev) => prev.filter((c) => c.comparison_id !== cid));
    } catch (err) {
      console.error("Failed to delete comparison:", err);
    }
  };

  // Delete Individual History
  const handleDeleteHistory = async (id: number, type: "search" | "comparison" = "search") => {
    try {
      await deleteHistoryItem(id, type);
      setSearchHistory((prev) => prev.filter((item) => item.id !== id));
    } catch (err) {
      console.error("Failed to delete history item:", err);
    }
  };

  // Clear All History
  const handleClearHistory = async () => {
    try {
      await clearAllHistory();
      setSearchHistory([]);
    } catch (err) {
      console.error("Failed to clear history:", err);
    }
  };

  // Handle Quick AI Search Submit
  const handleAiSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!aiSearchPrompt.trim()) return;
    if (onNavigate) {
      onNavigate("chat", aiSearchPrompt.trim());
    }
  };

  const handlePromptChipClick = (prompt: string) => {
    if (onNavigate) {
      onNavigate("chat", prompt);
    }
  };

  // Wishlist toggle from recommendation card
  const handleWishlistToggle = async (product: Product) => {
    const isWishlisted = wishlistItems.some((p) => p.id === product.id);
    try {
      if (isWishlisted) {
        await removeFavorite(product.id);
        setWishlistItems((prev) => prev.filter((p) => p.id !== product.id));
      } else {
        await addFavorite(product.id);
        setWishlistItems((prev) => [product, ...prev]);
      }
    } catch (err) {
      console.error("Error updating wishlist:", err);
    }
  };

  const activeAvatarUrl = avatarPreview || getAssetUrl(avatar);

  const quickActionPrompts = [
    "Best gaming laptop under ₹80,000 with 16GB RAM",
    "Compare ASUS Vivobook OLED vs Lenovo IdeaPad",
    "Find high battery life laptops for programming",
    "Explain difference between RTX 3050 vs RTX 4050 TDP",
  ];

  return (
    <div className="py-8 space-y-8 pb-32">
      {/* ============================================================ */}
      {/* 1. PROFILE / WELCOME HEADER */}
      {/* ============================================================ */}
      <div className="bg-white border border-slate-200/90 rounded-3xl p-6 sm:p-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-6 shadow-sm">
        <div className="flex items-center gap-5">
          <div className="relative group">
            <div className="w-20 h-20 rounded-2xl overflow-hidden bg-slate-100 border-2 border-blue-500 shadow-md shrink-0">
              <img
                src={activeAvatarUrl}
                alt={name || "User"}
                className="w-full h-full object-cover"
              />
            </div>
            <button
              onClick={() => setActiveTab("profile")}
              className="absolute inset-0 bg-black/40 text-white rounded-2xl opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity cursor-pointer text-[10px] font-bold"
              title="Change Avatar"
            >
              <Camera className="w-4 h-4" />
            </button>
          </div>

          <div>
            <div className="flex items-center gap-2.5 flex-wrap">
              <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
                {name || "Hardware Enthusiast"}
              </h1>
              <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider ${
                user?.isAdmin ? "bg-purple-600 text-white" : "bg-blue-50 text-blue-700 border border-blue-200"
              }`}>
                {user?.isAdmin ? "Admin" : "Verified Member"}
              </span>
            </div>
            <p className="text-xs font-bold text-blue-600 mt-0.5">{title || "Product Architecture Enthusiast"}</p>
            <p className="text-xs text-slate-400 font-medium mt-0.5">{email || "user@example.com"} • {location || "India"}</p>
          </div>
        </div>

        {/* Profile Navigation Tabs & Edit Profile CTA */}
        <div className="flex items-center gap-2 flex-wrap">
          {[
            { id: "overview", label: "Dashboard Overview" },
            { id: "profile", label: "Profile & Metrics" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-3.5 py-2 rounded-xl text-xs font-extrabold capitalize transition-all cursor-pointer flex items-center gap-1.5 ${
                activeTab === tab.id
                  ? "bg-blue-600 text-white shadow-md shadow-blue-500/20"
                  : "bg-slate-100 hover:bg-slate-200 text-slate-700"
              }`}
            >
              <span>{tab.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Global Alerts Banner */}
      {saveSuccessMsg && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-2xl text-xs font-bold flex items-center gap-2 shadow-2xs"
        >
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{saveSuccessMsg}</span>
        </motion.div>
      )}

      {saveErrorMsg && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 bg-rose-50 border border-rose-200 text-rose-800 rounded-2xl text-xs font-bold flex items-center gap-2 shadow-2xs"
        >
          <span className="w-2 h-2 rounded-full bg-rose-600" />
          <span>{saveErrorMsg}</span>
        </motion.div>
      )}

      {/* ============================================================ */}
      {/* TAB 1: DASHBOARD OVERVIEW */}
      {/* ============================================================ */}
      {activeTab === "overview" && (
        <div className="space-y-8">
          {/* ============================================================ */}
          {/* 2. QUICK ACTIONS ROW */}
          {/* ============================================================ */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <button
              onClick={() => onNavigate && onNavigate("home")}
              className="p-4 bg-white hover:bg-blue-50/60 border border-slate-200 hover:border-blue-300 rounded-2xl text-left transition-all group shadow-2xs cursor-pointer"
            >
              <Compass className="w-5 h-5 text-blue-600 mb-2 group-hover:scale-110 transition-transform" />
              <div className="text-xs font-black text-slate-900">Explore Catalog</div>
              <div className="text-[11px] text-slate-400 font-semibold mt-0.5">2,467+ Verified Laptops</div>
            </button>

            <button
              onClick={() => onNavigate && onNavigate("compare")}
              className="p-4 bg-white hover:bg-indigo-50/60 border border-slate-200 hover:border-indigo-300 rounded-2xl text-left transition-all group shadow-2xs cursor-pointer"
            >
              <Scale className="w-5 h-5 text-indigo-600 mb-2 group-hover:scale-110 transition-transform" />
              <div className="text-xs font-black text-slate-900">Spec Comparison</div>
              <div className="text-[11px] text-slate-400 font-semibold mt-0.5">Side-by-side matrices</div>
            </button>

            <button
              onClick={() => onNavigate && onNavigate("documents")}
              className="p-4 bg-white hover:bg-purple-50/60 border border-slate-200 hover:border-purple-300 rounded-2xl text-left transition-all group shadow-2xs cursor-pointer"
            >
              <FileText className="w-5 h-5 text-purple-600 mb-2 group-hover:scale-110 transition-transform" />
              <div className="text-xs font-black text-slate-900">Upload Datasheet</div>
              <div className="text-[11px] text-slate-400 font-semibold mt-0.5">RAG Document Engine</div>
            </button>

            <button
              onClick={() => onNavigate && onNavigate("wishlist")}
              className="p-4 bg-white hover:bg-rose-50/60 border border-slate-200 hover:border-rose-300 rounded-2xl text-left transition-all group shadow-2xs cursor-pointer"
            >
              <Heart className="w-5 h-5 text-rose-500 mb-2 group-hover:scale-110 transition-transform" />
              <div className="text-xs font-black text-slate-900">Saved Wishlist</div>
              <div className="text-[11px] text-slate-400 font-semibold mt-0.5">
                {stats?.wishlist_count || wishlistItems.length} Tracked Gadgets
              </div>
            </button>
          </div>

          {/* ============================================================ */}
          {/* PERSONALIZED RECOMMENDATIONS ("Recommended For You") */}
          {/* ============================================================ */}
          <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 space-y-6 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-xl font-black text-slate-900 flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-blue-600" /> Recommended For You
                </h3>
                <p className="text-xs text-slate-500 font-medium mt-0.5">
                  Tailored based on your saved budget (₹{preferences.budgetMin?.toLocaleString()} - ₹{preferences.budgetMax?.toLocaleString()}) and {preferences.aiStyle} priority
                </p>
              </div>

              <button
                onClick={() => onNavigate && onNavigate("home")}
                className="text-xs font-bold text-blue-600 hover:text-blue-700 flex items-center gap-1 cursor-pointer"
              >
                View all <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>

            {personalizedRecs.length === 0 ? (
              <div className="py-8 text-center text-xs text-slate-400 bg-slate-50 rounded-2xl border border-dashed border-slate-200">
                Loading tailored recommendations from MySQL database...
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
                {personalizedRecs.map((rec) => {
                  const p = rec.product;
                  const isWish = wishlistItems.some((w) => w.id === p.id);
                  return (
                    <div
                      key={p.id}
                      className="bg-slate-50/70 hover:bg-white border border-slate-200 hover:border-blue-300 rounded-2xl p-4 transition-all shadow-2xs space-y-3 flex flex-col justify-between"
                    >
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] font-black uppercase text-blue-600 bg-blue-50 px-2 py-0.5 rounded-lg border border-blue-100">
                            {p.brand}
                          </span>
                          <span className="text-[11px] font-black text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-lg border border-emerald-100">
                            {rec.match_score}% Match
                          </span>
                        </div>

                        <h4 className="text-xs font-bold text-slate-900 line-clamp-2 leading-snug">
                          {p.name}
                        </h4>

                        <div className="text-sm font-black text-slate-900">
                          ₹{Number(p.price).toLocaleString()}
                        </div>

                        {rec.reason && (
                          <p className="text-[11px] text-slate-500 font-medium line-clamp-2 leading-relaxed bg-white/80 p-2 rounded-xl border border-slate-100">
                            {rec.reason}
                          </p>
                        )}
                      </div>

                      <div className="pt-2 border-t border-slate-200/80 flex items-center justify-between gap-2">
                        <button
                          onClick={() => handleWishlistToggle(p)}
                          className={`p-2 rounded-xl border transition-colors cursor-pointer ${
                            isWish
                              ? "bg-rose-50 border-rose-200 text-rose-600"
                              : "bg-white border-slate-200 text-slate-400 hover:text-rose-500"
                          }`}
                          title={isWish ? "Remove from Wishlist" : "Save to Wishlist"}
                        >
                          <Heart className="w-3.5 h-3.5 fill-current" />
                        </button>

                        <button
                          onClick={() => onNavigate && onNavigate("home")}
                          className="flex-1 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-[11px] font-bold transition-colors cursor-pointer text-center"
                        >
                          Inspect Specs
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* ============================================================ */}
          {/* 6. CATALOG ANALYTICS CHARTS (Recharts) */}
          {/* ============================================================ */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* 1. Category Distribution Pie Chart */}
            <div className="bg-white border border-slate-200 rounded-3xl p-6 space-y-4 shadow-sm">
              <h3 className="text-base font-black text-slate-900 flex items-center gap-2">
                <Layers className="w-5 h-5 text-purple-600" /> Category Breakdown
              </h3>
              <p className="text-xs text-slate-500 font-medium">Laptops, Smartphones, and Tablets</p>

              <div className="h-64 w-full pt-2">
                {categoryDistribution.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={categoryDistribution}
                        dataKey="count"
                        nameKey="category"
                        cx="50%"
                        cy="50%"
                        outerRadius={75}
                        label={({ category, percentage }: any) => `${category} (${percentage}%)`}
                      >
                        {categoryDistribution.map((entry, index) => (
                          <Cell key={`cat-${index}`} fill={entry.color || BRAND_COLORS[index % BRAND_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip contentStyle={{ borderRadius: "1rem", fontWeight: 700, fontSize: "12px" }} />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-xs text-slate-400">
                    Loading category distribution...
                  </div>
                )}
              </div>
            </div>

            {/* 2. Price Distribution Bar Chart */}
            <div className="bg-white border border-slate-200 rounded-3xl p-6 space-y-4 shadow-sm">
              <h3 className="text-base font-black text-slate-900 flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-blue-600" /> Price Segmentation
              </h3>
              <p className="text-xs text-slate-500 font-medium">Product counts across budget tiers in MySQL</p>

              <div className="h-64 w-full pt-2">
                {priceSegmentation.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={priceSegmentation}>
                      <XAxis dataKey="range" tick={{ fontSize: 10, fontWeight: 700 }} />
                      <YAxis tick={{ fontSize: 10, fontWeight: 700 }} />
                      <Tooltip
                        contentStyle={{
                          borderRadius: "1rem",
                          fontWeight: 700,
                          fontSize: "12px",
                          border: "1px solid #E2E8F0",
                          boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.1)",
                        }}
                      />
                      <Bar dataKey="count" fill="#2563EB" radius={[8, 8, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-xs text-slate-400">
                    Loading price distribution...
                  </div>
                )}
              </div>
            </div>

            {/* 3. Popular Brands Pie Chart */}
            <div className="bg-white border border-slate-200 rounded-3xl p-6 space-y-4 shadow-sm">
              <h3 className="text-base font-black text-slate-900 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-indigo-600" /> Leading Brand Shares
              </h3>
              <p className="text-xs text-slate-500 font-medium">OEM distribution calculated across active inventory</p>

              <div className="h-64 w-full pt-2">
                {brandMarketShare.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={brandMarketShare}
                        dataKey="count"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        outerRadius={75}
                        label={({ name, percentage }: any) => `${name} (${percentage}%)`}
                      >
                        {brandMarketShare.map((_, index) => (
                          <Cell key={`cell-${index}`} fill={BRAND_COLORS[index % BRAND_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip contentStyle={{ borderRadius: "1rem", fontWeight: 700, fontSize: "12px" }} />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-xs text-slate-400">
                    Loading brand distribution...
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* ============================================================ */}
          {/* 7. RECENT ACTIVITY & SEARCH HISTORY */}
          {/* ============================================================ */}
          <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 space-y-4 shadow-sm">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-black text-slate-900 flex items-center gap-2">
                <Activity className="w-5 h-5 text-blue-600" /> Recent Search & AI Query Activity
              </h3>
              <button
                onClick={() => setActiveTab("history")}
                className="text-xs font-bold text-blue-600 hover:underline cursor-pointer"
              >
                Manage History
              </button>
            </div>

            {searchHistory.length === 0 ? (
              <p className="text-xs text-slate-400 py-4 text-center">No recent searches logged yet.</p>
            ) : (
              <div className="divide-y divide-slate-100">
                {searchHistory.slice(0, 5).map((s) => (
                  <div key={s.id} className="py-3 flex items-center justify-between gap-4 text-xs">
                    <div className="flex items-center gap-2.5">
                      <Search className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                      <span className="font-bold text-slate-900">&quot;{s.query_text}&quot;</span>
                    </div>
                    <span className="text-[11px] text-slate-400 font-semibold">
                      {new Date(s.created_at).toLocaleDateString()}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* TAB 2: PROFILE & AVATAR SETTINGS */}
      {/* ============================================================ */}
      {activeTab === "profile" && (
        <div className="space-y-6">
          {/* Avatar Management Card */}
          <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 space-y-6 shadow-sm">
            <h2 className="text-xl font-black text-slate-900">Profile Photo Management</h2>
            <p className="text-xs text-slate-500 font-medium">
              Upload a profile photo. Supported formats: JPG, JPEG, PNG, WEBP (Max 5MB). Photo is stored securely and displayed across the platform.
            </p>

            <div className="flex flex-col sm:flex-row items-center gap-6 pt-2">
              <div className="w-24 h-24 rounded-2xl overflow-hidden bg-slate-100 border-2 border-blue-500 shadow-md shrink-0">
                <img
                  src={activeAvatarUrl}
                  alt={name}
                  className="w-full h-full object-cover"
                />
              </div>

              <div className="flex items-center gap-3 flex-wrap">
                <input
                  type="file"
                  id="avatar-file-input"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={handlePhotoUpload}
                  className="hidden"
                  disabled={isUploadingPhoto}
                />
                <label
                  htmlFor="avatar-file-input"
                  className="px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold shadow-md shadow-blue-500/20 cursor-pointer flex items-center gap-2 transition-colors"
                >
                  {isUploadingPhoto ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Camera className="w-4 h-4" />
                  )}
                  <span>Change Photo</span>
                </label>

                <button
                  type="button"
                  onClick={handleRemovePhoto}
                  disabled={isUploadingPhoto}
                  className="px-4 py-2.5 bg-slate-100 hover:bg-rose-50 hover:text-rose-700 text-slate-700 rounded-xl text-xs font-bold border border-slate-200 transition-colors cursor-pointer"
                >
                  Remove Photo
                </button>
              </div>
            </div>
          </div>

          {/* Account Metrics Summary */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-white border border-slate-200 rounded-3xl p-5 shadow-sm space-y-1">
              <div className="text-[11px] font-extrabold text-blue-600 uppercase tracking-wider flex items-center gap-1.5">
                <MessageSquare className="w-4 h-4" /> Total AI Chats
              </div>
              <div className="text-2xl sm:text-3xl font-black text-slate-900">
                {user?.totalChats || userConversations.reduce((acc, c) => acc + (c.message_count || 0), 0) || 0}
              </div>
              <p className="text-[11px] text-slate-400 font-medium">Persisted across {userConversations.length} conversations in MySQL</p>
            </div>

            <div className="bg-white border border-slate-200 rounded-3xl p-5 shadow-sm space-y-1">
              <div className="text-[11px] font-extrabold text-indigo-600 uppercase tracking-wider flex items-center gap-1.5">
                <Scale className="w-4 h-4" /> Saved Comparisons
              </div>
              <div className="text-2xl sm:text-3xl font-black text-slate-900">
                {user?.totalComparisons || savedComparisons.length || 0}
              </div>
              <p className="text-[11px] text-slate-400 font-medium">Saved hardware matrices and winner scores</p>
            </div>

            <div className="bg-white border border-slate-200 rounded-3xl p-5 shadow-sm space-y-1">
              <div className="text-[11px] font-extrabold text-rose-600 uppercase tracking-wider flex items-center gap-1.5">
                <Heart className="w-4 h-4" /> Saved Wishlist
              </div>
              <div className="text-2xl sm:text-3xl font-black text-slate-900">
                {user?.wishlistCount || wishlistItems.length || 0}
              </div>
              <p className="text-[11px] text-slate-400 font-medium">Shortlisted laptops, phones & tablets</p>
            </div>
          </div>

          {/* Profile Form */}
          <form onSubmit={handleSaveProfile} className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 space-y-6 shadow-sm">
            <h2 className="text-xl font-black text-slate-900">Personal Information</h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              <div>
                <label className="text-xs font-bold text-slate-500 block mb-1">Full Name</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-xs font-bold text-slate-900 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-slate-500 block mb-1">Email Address</label>
                <input
                  type="email"
                  disabled
                  value={email}
                  className="w-full bg-slate-100 border border-slate-200 rounded-xl px-4 py-2.5 text-xs font-bold text-slate-400 cursor-not-allowed"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-slate-500 block mb-1">Professional Title</label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Senior Hardware Architect"
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-xs font-bold text-slate-900 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-slate-500 block mb-1">Phone Number</label>
                <input
                  type="text"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="+91 98765 43210"
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-xs font-bold text-slate-900 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="sm:col-span-2">
                <label className="text-xs font-bold text-slate-500 block mb-1">Location</label>
                <input
                  type="text"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  placeholder="Bengaluru, India"
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-xs font-bold text-slate-900 focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>

            <div>
              <label className="text-xs font-bold text-slate-500 block mb-1">Bio / Profile Summary</label>
              <textarea
                rows={3}
                value={bio}
                onChange={(e) => setBio(e.target.value)}
                placeholder="Share your hardware interests and tech background..."
                className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 text-xs font-medium text-slate-900 focus:outline-none focus:border-blue-500"
              />
            </div>

            {/* Change Password Sub-Section */}
            <div className="pt-6 border-t border-slate-200 space-y-4">
              <h3 className="text-sm font-black text-slate-900 flex items-center gap-1.5">
                <Lock className="w-4 h-4 text-blue-600" /> Change Account Password
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="text-xs font-bold text-slate-500 block mb-1">Current Password</label>
                  <input
                    type="password"
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    placeholder="Current password"
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-xs font-bold text-slate-900 focus:outline-none focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="text-xs font-bold text-slate-500 block mb-1">New Password</label>
                  <input
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="New password (min 6 chars)"
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-xs font-bold text-slate-900 focus:outline-none focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="text-xs font-bold text-slate-500 block mb-1">Confirm Password</label>
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Confirm new password"
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-xs font-bold text-slate-900 focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                type="submit"
                disabled={isSaving}
                className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-black rounded-xl shadow-md shadow-blue-500/20 disabled:opacity-50 cursor-pointer"
              >
                {isSaving ? "Saving Changes..." : "Save Profile Details"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* ============================================================ */}
      {/* TAB 3: MY CONVERSATIONS (STORED IN MYSQL) */}
      {/* ============================================================ */}
      {activeTab === "conversations" && (
        <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 space-y-6 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-black text-slate-900 flex items-center gap-2">
                <MessageSquare className="w-5 h-5 text-blue-600" /> My AI Conversations
              </h2>
              <p className="text-xs text-slate-500 font-medium">
                Authoritative AI chat history stored in MySQL database for your account
              </p>
            </div>
            <button
              onClick={() => onNavigate && onNavigate("chat")}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold shadow-md shadow-blue-500/20 flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              Start New Chat <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {userConversations.length === 0 ? (
            <div className="text-center py-12 bg-slate-50 rounded-2xl border border-dashed border-slate-200 p-6 space-y-2">
              <MessageSquare className="w-10 h-10 mx-auto text-slate-300" />
              <p className="text-xs font-bold text-slate-600">No conversations logged yet.</p>
              <p className="text-xs text-slate-400">Ask questions in the Ask AI view to automatically save chat history.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {userConversations.map((c) => (
                <div
                  key={c.conversation_id}
                  className="p-5 bg-slate-50/80 border border-slate-200/90 rounded-2xl hover:border-blue-300 hover:bg-white transition-all space-y-3 shadow-2xs flex flex-col justify-between"
                >
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-black text-slate-900 truncate">{c.title}</span>
                      <span className="text-[10px] font-black text-blue-700 bg-blue-100 px-2 py-0.5 rounded-md shrink-0">
                        {c.message_count} messages
                      </span>
                    </div>
                    <p className="text-xs text-slate-600 font-medium line-clamp-2 leading-relaxed">
                      {c.last_message}
                    </p>
                    {c.products_discussed && c.products_discussed.length > 0 && (
                      <div className="flex items-center gap-1.5 flex-wrap pt-1">
                        {c.products_discussed.slice(0, 3).map((pname, pidx) => (
                          <span
                            key={pidx}
                            className="text-[10px] font-bold bg-white text-slate-700 border border-slate-200 px-2 py-0.5 rounded-md"
                          >
                            {pname}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="pt-2 border-t border-slate-200/70 flex items-center justify-between">
                    <span className="text-[11px] text-slate-400 font-semibold flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5" />
                      {c.updated_at ? new Date(c.updated_at).toLocaleDateString() : "Recent"}
                    </span>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleDeleteConversation(c.conversation_id)}
                        className="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-rose-50 transition-colors"
                        title="Delete conversation"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => onNavigate && onNavigate("chat")}
                        className="px-3 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-lg text-xs font-bold flex items-center gap-1 transition-colors cursor-pointer"
                      >
                        Resume Chat <ArrowRight className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ============================================================ */}
      {/* TAB 4: MY SAVED COMPARISONS (STORED IN MYSQL) */}
      {/* ============================================================ */}
      {activeTab === "comparisons" && (
        <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 space-y-6 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-black text-slate-900 flex items-center gap-2">
                <Scale className="w-5 h-5 text-blue-600" /> Saved Product Comparisons
              </h2>
              <p className="text-xs text-slate-500 font-medium">
                Hardware spec comparison reports and winner analysis saved in database
              </p>
            </div>
            <button
              onClick={() => onNavigate && onNavigate("compare")}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold shadow-md shadow-blue-500/20 flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              New Comparison <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {savedComparisons.length === 0 ? (
            <div className="text-center py-12 bg-slate-50 rounded-2xl border border-dashed border-slate-200 p-6 space-y-2">
              <Scale className="w-10 h-10 mx-auto text-slate-300" />
              <p className="text-xs font-bold text-slate-600">No saved comparisons found.</p>
              <p className="text-xs text-slate-400">Compare products to automatically record comparison summaries.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {savedComparisons.map((comp) => {
                const winnerName = comp.comparison_result?.winner_name;
                const winnerSummary = comp.summary || comp.comparison_result?.winner_summary;
                const comparedProds = comp.comparison_result?.products || [];

                return (
                  <div
                    key={comp.comparison_id}
                    className="p-5 bg-slate-50/80 border border-slate-200/90 rounded-2xl hover:border-blue-300 hover:bg-white transition-all space-y-3 shadow-2xs flex flex-col justify-between"
                  >
                    <div className="space-y-2">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-[11px] font-black text-blue-600 uppercase tracking-wider">
                          {comp.product_ids?.length || 2} Products Compared
                        </span>
                        {winnerName && (
                          <span className="text-[10px] font-black text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-md flex items-center gap-1">
                            <Star className="w-3 h-3 fill-emerald-600 text-emerald-600" /> Winner: {winnerName}
                          </span>
                        )}
                      </div>

                      {comparedProds.length > 0 && (
                        <div className="flex items-center gap-2 flex-wrap">
                          {comparedProds.map((p: any, idx: number) => (
                            <span
                              key={idx}
                              className="text-xs font-bold bg-white text-slate-800 border border-slate-200 px-2.5 py-1 rounded-xl shadow-2xs"
                            >
                              {p.brand} {p.name}
                            </span>
                          ))}
                        </div>
                      )}

                      {winnerSummary && (
                        <p className="text-xs text-slate-600 font-medium leading-relaxed bg-white/60 p-2.5 rounded-xl border border-slate-100">
                          {winnerSummary}
                        </p>
                      )}
                    </div>

                    <div className="pt-2 border-t border-slate-200/70 flex items-center justify-between">
                      <span className="text-[11px] text-slate-400 font-semibold flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5" />
                        {comp.created_at ? new Date(comp.created_at).toLocaleDateString() : "Recent"}
                      </span>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleDeleteSavedComparison(comp.comparison_id)}
                          className="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-rose-50 transition-colors"
                          title="Delete comparison"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => onNavigate && onNavigate("compare")}
                          className="px-3 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-lg text-xs font-bold flex items-center gap-1 transition-colors cursor-pointer"
                        >
                          View Matrix <ArrowRight className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}



      {/* ============================================================ */}
      {/* TAB 4: SEARCH & COMPARISON HISTORY */}
      {/* ============================================================ */}
      {activeTab === "history" && (
        <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 space-y-6 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-black text-slate-900 flex items-center gap-2">
                <History className="w-5 h-5 text-blue-600" /> Search & Comparison Activity
              </h2>
              <p className="text-xs text-slate-500 font-medium">Logged queries and comparisons stored in database</p>
            </div>

            <button
              onClick={handleClearHistory}
              className="px-4 py-2 bg-rose-50 hover:bg-rose-100 text-rose-700 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <Trash2 className="w-3.5 h-3.5" /> Clear All History
            </button>
          </div>

          <div className="space-y-4">
            <h3 className="text-sm font-black text-slate-900 uppercase tracking-wider text-xs">Recent AI Searches</h3>
            {searchHistory.length === 0 ? (
              <p className="text-xs text-slate-400 py-4">No logged searches yet.</p>
            ) : (
              <div className="space-y-2">
                {searchHistory.map((s) => (
                  <div
                    key={s.id}
                    className="flex items-center justify-between p-3.5 bg-slate-50 border border-slate-200 rounded-2xl text-xs"
                  >
                    <div>
                      <span className="font-bold text-slate-900">&quot;{s.query_text}&quot;</span>
                      <span className="text-[11px] text-slate-400 ml-3">
                        {new Date(s.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    <button
                      onClick={() => handleDeleteHistory(s.id, "search")}
                      className="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg cursor-pointer"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* FOOTER */}
      {/* ============================================================ */}
      <footer className="pt-8 border-t border-slate-200 text-center text-xs text-slate-400 space-y-1">
        <p className="font-bold text-slate-600">VersusAI — Next-Gen Hardware Comparison & Recommendation Platform</p>
        <p>© 2026 VersusAI. Grounded with verified MySQL inventory & RAG datasheets.</p>
      </footer>
    </div>
  );
}
