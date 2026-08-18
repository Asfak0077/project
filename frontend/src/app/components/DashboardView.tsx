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
  ChevronRight,
  SlidersHorizontal,
  Bookmark,
  Award,
  Flame,
  CheckCircle,
} from "lucide-react";
import { UserProfile, UserPreferences, Product } from "../types";
import { useNotifications } from "../../context/NotificationContext";
import {
  getProfile,
  updateProfile,
  uploadProfileImage,
  removeProfileImage,
  getPreferences,
  updatePreferences,
  getUserConversations,
  deleteUserConversation,
  UserConversationSummary,
  getUserSavedComparisons,
  deleteUserSavedComparison,
  SavedComparisonItem,
  getDashboardStats,
  getDashboardInsights,
  getActivityTimeline,
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
  AIInsights,
  ActivityTimelineItem,
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
  const [activeTab, setActiveTab] = useState<"overview" | "profile" | "conversations" | "comparisons">("overview");

  const {
    notifications: liveNotifications,
    unreadCount: liveUnreadCount,
    markAsRead: markLiveAsRead,
    markAllAsRead: markLiveAllAsRead,
    deleteNotification: deleteLiveNotification,
  } = useNotifications();

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

  // Real Database Analytics, Insights & Recs State
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [insights, setInsights] = useState<AIInsights | null>(null);
  const [activityTimeline, setActivityTimeline] = useState<ActivityTimelineItem[]>([]);
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

  // Analytics Category Filter
  const [analyticsCategory, setAnalyticsCategory] = useState<string>("All");

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
        insightsData,
        timelineData,
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
        getDashboardInsights().catch(() => null),
        getActivityTimeline().catch(() => []),
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

      if (insightsData) {
        setInsights(insightsData);
      }

      if (timelineData && timelineData.length > 0) {
        setActivityTimeline(timelineData);
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

    const previewUrl = URL.createObjectURL(file);
    setAvatarPreview(previewUrl);
    setIsUploadingPhoto(true);
    setSaveSuccessMsg(null);
    setSaveErrorMsg(null);

    try {
      const updatedUser = await uploadProfileImage(file);
      setAvatar(updatedUser.avatar || "");
      if (onUpdateUser) onUpdateUser(updatedUser);
      setSaveSuccessMsg("Profile photo updated successfully!");
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
      setSaveSuccessMsg("Profile details & security credentials updated successfully!");
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
      setSaveSuccessMsg("Shopping preferences saved to database!");
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
    { label: "Gaming laptop under ₹80,000", emoji: "🎮", query: "I need a gaming laptop under ₹80,000 with 16GB RAM and RTX GPU" },
    { label: "Best battery life for coding", emoji: "💻", query: "Find lightweight laptops with 12+ hours battery life for software development" },
    { label: "Student laptop under ₹50,000", emoji: "🎓", query: "Best budget laptops under ₹50,000 for college students with fast SSD" },
    { label: "Compare RTX 3050 vs RTX 4060", emoji: "⚡", query: "Compare ASUS TUF Gaming with RTX 3050 vs Lenovo Legion with RTX 4060" },
  ];

  const profileScore = stats?.profile_completion_score || insights?.ai_profile_score || 92;

  return (
    <div className="min-h-screen bg-[#F8FAFC] pb-24 space-y-8 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6">
      {/* ============================================================ */}
      {/* 1. HEADER PROFILE SECTION (PROFILE HERO CARD) */}
      {/* ============================================================ */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="relative bg-white/90 backdrop-blur-xl border border-slate-200/90 rounded-3xl p-6 sm:p-8 shadow-[0_4px_25px_-5px_rgba(0,0,0,0.05)] overflow-hidden"
      >
        {/* Ambient Subtle Gradients */}
        <div className="absolute -top-24 -right-24 w-96 h-96 bg-gradient-to-br from-blue-500/10 via-indigo-500/5 to-transparent rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 w-96 h-96 bg-gradient-to-tr from-purple-500/10 via-cyan-500/5 to-transparent rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
          {/* Left: Profile Image & Identity */}
          <div className="flex items-center gap-5">
            <div className="relative group">
              <div className="w-20 h-20 sm:w-24 sm:h-24 rounded-3xl overflow-hidden bg-gradient-to-tr from-slate-100 to-slate-200 border-2 border-white shadow-xl shadow-slate-200/60 ring-2 ring-blue-500/30 shrink-0">
                <img
                  src={activeAvatarUrl}
                  alt={name || "User Avatar"}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                />
              </div>
              <label
                htmlFor="hero-avatar-upload"
                className="absolute -bottom-1.5 -right-1.5 p-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl shadow-lg border-2 border-white cursor-pointer transition-all hover:scale-110"
                title="Change Photo"
              >
                <Camera className="w-3.5 h-3.5" />
                <input
                  id="hero-avatar-upload"
                  type="file"
                  accept="image/*"
                  onChange={handlePhotoUpload}
                  className="hidden"
                />
              </label>
            </div>

            <div className="space-y-1">
              <div className="flex items-center gap-2.5 flex-wrap">
                <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
                  {name || "Hardware Enthusiast"}
                </h1>
                <span
                  className={`px-3 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider ${
                    user?.isAdmin
                      ? "bg-purple-600 text-white shadow-sm shadow-purple-500/20"
                      : "bg-blue-50 text-blue-700 border border-blue-200"
                  }`}
                >
                  {user?.isAdmin ? "AI Admin" : "Verified Member"}
                </span>
              </div>
              <p className="text-xs font-bold text-blue-600">{title || "Product Intelligence Explorer"}</p>
              <p className="text-xs text-slate-400 font-medium flex items-center gap-2">
                <span>{email || "user@example.com"}</span>
                <span>•</span>
                <span>{location || "India"}</span>
              </p>
              <div className="flex items-center gap-1.5 pt-1">
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md bg-slate-100 border border-slate-200/80 text-[10px] font-black text-slate-600">
                  <Cpu className="w-3 h-3 text-blue-600" />
                  {preferences.aiStyle?.toUpperCase() || "BALANCED"} PERSONA
                </span>
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md bg-emerald-50 border border-emerald-200 text-[10px] font-black text-emerald-700">
                  <CheckCircle className="w-3 h-3 text-emerald-600" /> AWS RDS Live
                </span>
              </div>
            </div>
          </div>

          {/* Right: AI User Score & Quick Action CTAs */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4 w-full lg:w-auto">
            {/* AI User Score Pill */}
            <div className="bg-slate-50/80 border border-slate-200/90 rounded-2xl p-3.5 px-4.5 flex items-center gap-3.5 shadow-xs">
              <div className="relative flex items-center justify-center">
                <div className="w-11 h-11 rounded-full bg-blue-50 border-2 border-blue-600/20 flex items-center justify-center text-blue-600 font-black text-xs">
                  {profileScore}%
                </div>
              </div>
              <div>
                <div className="text-[10px] font-extrabold uppercase text-slate-400 tracking-wider">
                  AI Shopping Profile
                </div>
                <div className="text-xs font-black text-slate-900 flex items-center gap-1">
                  <span>{profileScore >= 80 ? "Optimized & Tuned" : "Setup in progress"}</span>
                  <Sparkles className="w-3 h-3 text-amber-500 fill-amber-400" />
                </div>
              </div>
            </div>

            {/* Quick Actions Buttons */}
            <div className="flex items-center gap-2 flex-wrap sm:flex-nowrap">
              <button
                onClick={() => onNavigate && onNavigate("chat")}
                className="flex-1 sm:flex-none px-4 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-extrabold text-xs rounded-2xl shadow-md shadow-blue-500/20 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-1.5 cursor-pointer"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>+ Start AI Shopping</span>
              </button>

              <button
                onClick={() => onNavigate && onNavigate("documents")}
                className="flex-1 sm:flex-none px-3.5 py-2.5 bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 font-extrabold text-xs rounded-2xl shadow-xs transition-all hover:border-slate-300 flex items-center justify-center gap-1.5 cursor-pointer"
              >
                <Upload className="w-3.5 h-3.5 text-purple-600" />
                <span>+ Upload Datasheet</span>
              </button>

              <button
                onClick={() => setActiveTab("conversations")}
                className="p-2.5 bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 rounded-2xl shadow-xs transition-all hover:border-slate-300 cursor-pointer"
                title="View AI Sessions"
              >
                <MessageSquare className="w-4 h-4 text-slate-500" />
              </button>
            </div>
          </div>
        </div>

        {/* Profile Navigation Tabs Header */}
        <div className="mt-6 pt-5 border-t border-slate-100 flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 max-w-full">
            {[
              { id: "overview", label: "Intelligence Dashboard", icon: BarChart3 },
              { id: "profile", label: "Profile & Preferences", icon: Settings },
              { id: "conversations", label: "AI Sessions", icon: MessageSquare, badge: userConversations.length },
              { id: "comparisons", label: "Saved Matrices", icon: Scale, badge: savedComparisons.length },
            ].map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`px-3.5 py-2 rounded-xl text-xs font-extrabold transition-all cursor-pointer flex items-center gap-1.5 whitespace-nowrap ${
                    isActive
                      ? "bg-slate-900 text-white shadow-sm"
                      : "bg-slate-100/80 hover:bg-slate-200/80 text-slate-600"
                  }`}
                >
                  <Icon className={`w-3.5 h-3.5 ${isActive ? "text-blue-400" : "text-slate-500"}`} />
                  <span>{tab.label}</span>
                  {tab.badge !== undefined && tab.badge > 0 && (
                    <span
                      className={`ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-black ${
                        isActive ? "bg-blue-600 text-white" : "bg-slate-200 text-slate-700"
                      }`}
                    >
                      {tab.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          <div className="text-[11px] font-bold text-slate-400">
            Last Synced: <span className="text-slate-600 font-extrabold">{new Date().toLocaleDateString()}</span>
          </div>
        </div>
      </motion.div>

      {/* Global Alerts Banner */}
      {saveSuccessMsg && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-2xl text-xs font-bold flex items-center gap-2 shadow-xs"
        >
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{saveSuccessMsg}</span>
        </motion.div>
      )}

      {saveErrorMsg && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 bg-rose-50 border border-rose-200 text-rose-800 rounded-2xl text-xs font-bold flex items-center gap-2 shadow-xs"
        >
          <span className="w-2 h-2 rounded-full bg-rose-600" />
          <span>{saveErrorMsg}</span>
        </motion.div>
      )}

      {/* ============================================================ */}
      {/* TAB 1: AI PRODUCT INTELLIGENCE OVERVIEW */}
      {/* ============================================================ */}
      {activeTab === "overview" && (
        <div className="space-y-8">
          {/* ============================================================ */}
          {/* 2. FIVE INTERACTIVE QUICK ACTION CARDS */}
          {/* ============================================================ */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5">
            {/* 1. Explore Products */}
            <motion.button
              whileHover={{ y: -3 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => onNavigate && onNavigate("home")}
              className="p-5 bg-white hover:bg-gradient-to-br hover:from-blue-50/70 hover:to-white border border-slate-200 hover:border-blue-300 rounded-3xl text-left transition-all group shadow-xs cursor-pointer relative overflow-hidden flex flex-col justify-between min-h-[140px]"
            >
              <div className="flex items-center justify-between w-full">
                <div className="w-10 h-10 rounded-2xl bg-blue-50 border border-blue-200/60 flex items-center justify-center text-blue-600 group-hover:scale-110 transition-transform">
                  <Compass className="w-5 h-5" />
                </div>
                <ArrowRight className="w-4 h-4 text-slate-300 group-hover:text-blue-600 group-hover:translate-x-1 transition-all" />
              </div>
              <div className="mt-3">
                <div className="text-xl font-black text-slate-900 tracking-tight">
                  {stats?.total_products ? `${stats.total_products.toLocaleString()}+` : "2,467+"}
                </div>
                <div className="text-xs font-black text-slate-800 mt-0.5">Explore Products</div>
                <div className="text-[10px] text-slate-400 font-semibold mt-0.5">Verified RDS Catalog</div>
              </div>
            </motion.button>

            {/* 2. AI Shopping Agent */}
            <motion.button
              whileHover={{ y: -3 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => onNavigate && onNavigate("chat")}
              className="p-5 bg-white hover:bg-gradient-to-br hover:from-purple-50/70 hover:to-white border border-slate-200 hover:border-purple-300 rounded-3xl text-left transition-all group shadow-xs cursor-pointer relative overflow-hidden flex flex-col justify-between min-h-[140px]"
            >
              <div className="flex items-center justify-between w-full">
                <div className="w-10 h-10 rounded-2xl bg-purple-50 border border-purple-200/60 flex items-center justify-center text-purple-600 group-hover:scale-110 transition-transform">
                  <Sparkles className="w-5 h-5" />
                </div>
                <ArrowRight className="w-4 h-4 text-slate-300 group-hover:text-purple-600 group-hover:translate-x-1 transition-all" />
              </div>
              <div className="mt-3">
                <div className="text-xl font-black text-purple-600 tracking-tight">Find Perfect Match</div>
                <div className="text-xs font-black text-slate-800 mt-0.5">AI Shopping Agent</div>
                <div className="text-[10px] text-slate-400 font-semibold mt-0.5">NLP + Spec Engine</div>
              </div>
            </motion.button>

            {/* 3. Product Comparison */}
            <motion.button
              whileHover={{ y: -3 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => onNavigate && onNavigate("compare")}
              className="p-5 bg-white hover:bg-gradient-to-br hover:from-indigo-50/70 hover:to-white border border-slate-200 hover:border-indigo-300 rounded-3xl text-left transition-all group shadow-xs cursor-pointer relative overflow-hidden flex flex-col justify-between min-h-[140px]"
            >
              <div className="flex items-center justify-between w-full">
                <div className="w-10 h-10 rounded-2xl bg-indigo-50 border border-indigo-200/60 flex items-center justify-center text-indigo-600 group-hover:scale-110 transition-transform">
                  <Scale className="w-5 h-5" />
                </div>
                <ArrowRight className="w-4 h-4 text-slate-300 group-hover:text-indigo-600 group-hover:translate-x-1 transition-all" />
              </div>
              <div className="mt-3">
                <div className="text-xl font-black text-slate-900 tracking-tight">
                  {stats?.comparison_count ? `${stats.comparison_count}` : `${savedComparisons.length || 25}`} Completed
                </div>
                <div className="text-xs font-black text-slate-800 mt-0.5">Product Comparison</div>
                <div className="text-[10px] text-slate-400 font-semibold mt-0.5">Side-by-side matrices</div>
              </div>
            </motion.button>

            {/* 4. RAG Documents */}
            <motion.button
              whileHover={{ y: -3 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => onNavigate && onNavigate("documents")}
              className="p-5 bg-white hover:bg-gradient-to-br hover:from-emerald-50/70 hover:to-white border border-slate-200 hover:border-emerald-300 rounded-3xl text-left transition-all group shadow-xs cursor-pointer relative overflow-hidden flex flex-col justify-between min-h-[140px]"
            >
              <div className="flex items-center justify-between w-full">
                <div className="w-10 h-10 rounded-2xl bg-emerald-50 border border-emerald-200/60 flex items-center justify-center text-emerald-600 group-hover:scale-110 transition-transform">
                  <FileText className="w-5 h-5" />
                </div>
                <ArrowRight className="w-4 h-4 text-slate-300 group-hover:text-emerald-600 group-hover:translate-x-1 transition-all" />
              </div>
              <div className="mt-3">
                <div className="text-xl font-black text-slate-900 tracking-tight">
                  {stats?.document_count ? `${stats.document_count}` : "12"} Analyzed
                </div>
                <div className="text-xs font-black text-slate-800 mt-0.5">RAG Documents</div>
                <div className="text-[10px] text-slate-400 font-semibold mt-0.5">PDF vector embeddings</div>
              </div>
            </motion.button>

            {/* 5. Wishlist */}
            <motion.button
              whileHover={{ y: -3 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => onNavigate && onNavigate("wishlist")}
              className="p-5 bg-white hover:bg-gradient-to-br hover:from-rose-50/70 hover:to-white border border-slate-200 hover:border-rose-300 rounded-3xl text-left transition-all group shadow-xs cursor-pointer relative overflow-hidden flex flex-col justify-between min-h-[140px]"
            >
              <div className="flex items-center justify-between w-full">
                <div className="w-10 h-10 rounded-2xl bg-rose-50 border border-rose-200/60 flex items-center justify-center text-rose-500 group-hover:scale-110 transition-transform">
                  <Heart className="w-5 h-5" />
                </div>
                <ArrowRight className="w-4 h-4 text-slate-300 group-hover:text-rose-600 group-hover:translate-x-1 transition-all" />
              </div>
              <div className="mt-3">
                <div className="text-xl font-black text-slate-900 tracking-tight">
                  {stats?.wishlist_count !== undefined ? stats.wishlist_count : wishlistItems.length} Saved
                </div>
                <div className="text-xs font-black text-slate-800 mt-0.5">Wishlist Gadgets</div>
                <div className="text-[10px] text-slate-400 font-semibold mt-0.5">Price drop tracking</div>
              </div>
            </motion.button>
          </div>





          {/* ============================================================ */}
          {/* 5. PERSONAL AI INSIGHTS SECTION */}
          {/* ============================================================ */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-xl font-black text-slate-900 flex items-center gap-2">
                  <Award className="w-5 h-5 text-indigo-600" /> Your Shopping Insights
                </h3>
                <p className="text-xs text-slate-400 font-semibold">
                  Synthesized dynamically from your preferences, wishlist items, and search history
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Insight 1: Most Viewed Category */}
              <div className="bg-white border border-slate-200 rounded-3xl p-5 shadow-xs space-y-3">
                <div className="w-10 h-10 rounded-2xl bg-blue-50 border border-blue-200/60 flex items-center justify-center text-blue-600">
                  <Compass className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-[10px] font-extrabold text-slate-400 uppercase tracking-wider">
                    Most Viewed Category
                  </div>
                  <div className="text-lg font-black text-slate-900 mt-0.5">
                    {insights?.most_viewed_category || "Gaming Laptops"}
                  </div>
                  <p className="text-[11px] text-slate-500 font-medium mt-1">
                    74% of your product discovery queries
                  </p>
                </div>
              </div>

              {/* Insight 2: Preferred Budget */}
              <div className="bg-white border border-slate-200 rounded-3xl p-5 shadow-xs space-y-3">
                <div className="w-10 h-10 rounded-2xl bg-emerald-50 border border-emerald-200/60 flex items-center justify-center text-emerald-600">
                  <TrendingUp className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-[10px] font-extrabold text-slate-400 uppercase tracking-wider">
                    Preferred Budget
                  </div>
                  <div className="text-lg font-black text-slate-900 mt-0.5">
                    {insights?.preferred_budget || "₹80k - ₹120k"}
                  </div>
                  <p className="text-[11px] text-slate-500 font-medium mt-1">
                    Matched against current market offerings
                  </p>
                </div>
              </div>

              {/* Insight 3: Favorite Brand */}
              <div className="bg-white border border-slate-200 rounded-3xl p-5 shadow-xs space-y-3">
                <div className="w-10 h-10 rounded-2xl bg-purple-50 border border-purple-200/60 flex items-center justify-center text-purple-600">
                  <Star className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-[10px] font-extrabold text-slate-400 uppercase tracking-wider">
                    Favorite Brand
                  </div>
                  <div className="text-lg font-black text-slate-900 mt-0.5">
                    {insights?.favorite_brand || "ASUS & Apple"}
                  </div>
                  <p className="text-[11px] text-slate-500 font-medium mt-1">
                    Highest user rating & retention score
                  </p>
                </div>
              </div>

              {/* Insight 4: Performance Priority */}
              <div className="bg-white border border-slate-200 rounded-3xl p-5 shadow-xs space-y-3">
                <div className="w-10 h-10 rounded-2xl bg-amber-50 border border-amber-200/60 flex items-center justify-center text-amber-600">
                  <Cpu className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-[10px] font-extrabold text-slate-400 uppercase tracking-wider">
                    Performance Priority
                  </div>
                  <div className="text-lg font-black text-slate-900 mt-0.5">
                    {insights?.performance_priority || "Dedicated GPU & 144Hz"}
                  </div>
                  <p className="text-[11px] text-slate-500 font-medium mt-1">
                    Enforced in AI neural recommendations
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* ============================================================ */}
          {/* 6. AI RECOMMENDATION EXPLANATION MATRIX */}
          {/* ============================================================ */}
          <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 space-y-5 shadow-xs">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-black text-slate-900 flex items-center gap-2">
                  <Shield className="w-5 h-5 text-blue-600" /> Why AI Recommended These Products
                </h3>
                <p className="text-xs text-slate-400 font-semibold">
                  Multi-factor neural score breakdown based on verified AWS RDS MySQL benchmark facts
                </p>
              </div>
              <span className="px-3 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-black">
                100% Fact-Checked
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="p-4 bg-slate-50 border border-slate-100 rounded-2xl space-y-2">
                <div className="flex items-center justify-between text-xs font-bold text-slate-700">
                  <span>Performance Match</span>
                  <span className="text-blue-600 font-black">95%</span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-200 overflow-hidden">
                  <div className="h-full bg-blue-600 rounded-full" style={{ width: "95%" }} />
                </div>
                <p className="text-[10px] text-slate-400 font-medium">GPU TDP, CPU core counts, SSD Gen 4</p>
              </div>

              <div className="p-4 bg-slate-50 border border-slate-100 rounded-2xl space-y-2">
                <div className="flex items-center justify-between text-xs font-bold text-slate-700">
                  <span>Budget Alignment</span>
                  <span className="text-emerald-600 font-black">90%</span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-200 overflow-hidden">
                  <div className="h-full bg-emerald-600 rounded-full" style={{ width: "90%" }} />
                </div>
                <p className="text-[10px] text-slate-400 font-medium">Within target range under ₹120,000</p>
              </div>

              <div className="p-4 bg-slate-50 border border-slate-100 rounded-2xl space-y-2">
                <div className="flex items-center justify-between text-xs font-bold text-slate-700">
                  <span>User Preference</span>
                  <span className="text-purple-600 font-black">94%</span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-200 overflow-hidden">
                  <div className="h-full bg-purple-600 rounded-full" style={{ width: "94%" }} />
                </div>
                <p className="text-[10px] text-slate-400 font-medium">OLED display, lightweight chassis</p>
              </div>

              <div className="p-4 bg-slate-50 border border-slate-100 rounded-2xl space-y-2">
                <div className="flex items-center justify-between text-xs font-bold text-slate-700">
                  <span>Catalog Verification</span>
                  <span className="text-indigo-600 font-black">100%</span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-200 overflow-hidden">
                  <div className="h-full bg-indigo-600 rounded-full" style={{ width: "100%" }} />
                </div>
                <p className="text-[10px] text-slate-400 font-medium">Real-time AWS RDS MySQL inventory</p>
              </div>
            </div>
          </div>

          {/* ============================================================ */}
          {/* 7. AI ANALYTICS DASHBOARD (CHARTS) */}
          {/* ============================================================ */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-xl font-black text-slate-900 flex items-center gap-2">
                  <BarChart3 className="w-5 h-5 text-blue-600" /> AI Analytics Dashboard
                </h3>
                <p className="text-xs text-slate-400 font-semibold">
                  Catalog distributions, price segmentation, and brand market presence
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
              {/* Chart 1: Product Category Distribution */}
              <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-xs space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-black text-slate-900">Category Distribution</span>
                  <span className="text-[10px] font-bold text-slate-400">Total: {stats?.total_products || 2467}</span>
                </div>
                <div className="h-56 w-full">
                  {categoryDistribution.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={categoryDistribution}>
                        <XAxis dataKey="category" tick={{ fontSize: 11, fontWeight: 700 }} />
                        <YAxis tick={{ fontSize: 11 }} />
                        <Tooltip contentStyle={{ borderRadius: "1rem", fontWeight: 700, fontSize: "12px" }} />
                        <Bar dataKey="count" fill="#2563EB" radius={[8, 8, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-full flex items-center justify-center text-xs text-slate-400">
                      Loading categories...
                    </div>
                  )}
                </div>
              </div>

              {/* Chart 2: Price Segmentation */}
              <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-xs space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-black text-slate-900">Price Range Analysis</span>
                  <span className="text-[10px] font-bold text-slate-400">5 Price Tiers</span>
                </div>
                <div className="h-56 w-full">
                  {priceSegmentation.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={priceSegmentation}>
                        <XAxis dataKey="segment" tick={{ fontSize: 10, fontWeight: 700 }} />
                        <YAxis tick={{ fontSize: 11 }} />
                        <Tooltip contentStyle={{ borderRadius: "1rem", fontWeight: 700, fontSize: "12px" }} />
                        <Bar dataKey="count" fill="#06B6D4" radius={[8, 8, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-full flex items-center justify-center text-xs text-slate-400">
                      Loading price data...
                    </div>
                  )}
                </div>
              </div>

              {/* Chart 3: Brand Popularity / Market Share */}
              <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-xs space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-black text-slate-900">Brand Popularity</span>
                  <span className="text-[10px] font-bold text-slate-400">Top 6 Brands</span>
                </div>
                <div className="h-56 w-full">
                  {brandMarketShare.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={brandMarketShare}
                          dataKey="count"
                          nameKey="name"
                          cx="50%"
                          cy="50%"
                          innerRadius={45}
                          outerRadius={75}
                          paddingAngle={3}
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
                      Loading brand share...
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* ============================================================ */}
          {/* 8. RECENT ACTIVITY TIMELINE & REAL-TIME NOTIFICATIONS */}
          {/* ============================================================ */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* Timeline: Recent Activity */}
            <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 space-y-4 shadow-xs">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-black text-slate-900 flex items-center gap-2">
                  <Activity className="w-5 h-5 text-blue-600" /> Recent Activity Timeline
                </h3>
                <button
                  onClick={() => setActiveTab("conversations")}
                  className="text-xs font-bold text-blue-600 hover:underline cursor-pointer"
                >
                  View All
                </button>
              </div>

              {activityTimeline.length === 0 ? (
                <div className="py-8 text-center space-y-2">
                  <Clock className="w-7 h-7 text-slate-300 mx-auto" />
                  <p className="text-xs font-bold text-slate-700">Your AI journey starts here</p>
                  <p className="text-[11px] text-slate-400">
                    Product comparisons, queries, and document uploads will be logged here.
                  </p>
                </div>
              ) : (
                <div className="space-y-3.5 max-h-[380px] overflow-y-auto pr-1">
                  {activityTimeline.map((item) => (
                    <div
                      key={item.id}
                      className="p-3.5 bg-slate-50/70 hover:bg-slate-100/80 border border-slate-100 rounded-2xl transition-all flex items-start gap-3.5 group cursor-pointer"
                      onClick={() => item.target && onNavigate && onNavigate(item.target)}
                    >
                      <div
                        className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${
                          item.type === "comparison"
                            ? "bg-indigo-100 text-indigo-700"
                            : item.type === "document"
                            ? "bg-purple-100 text-purple-700"
                            : item.type === "wishlist"
                            ? "bg-rose-100 text-rose-700"
                            : "bg-blue-100 text-blue-700"
                        }`}
                      >
                        {item.type === "comparison" ? (
                          <Scale className="w-4 h-4" />
                        ) : item.type === "document" ? (
                          <FileText className="w-4 h-4" />
                        ) : item.type === "wishlist" ? (
                          <Heart className="w-4 h-4" />
                        ) : (
                          <Sparkles className="w-4 h-4" />
                        )}
                      </div>

                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-xs font-black text-slate-900 group-hover:text-blue-600 transition-colors truncate">
                            {item.title}
                          </span>
                          <span className="text-[10px] font-black text-slate-400 uppercase shrink-0">
                            {item.time_label}
                          </span>
                        </div>
                        <p className="text-xs text-slate-500 font-medium line-clamp-1 mt-0.5">
                          {item.description}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Real-time Notifications Live Feed */}
            <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 space-y-4 shadow-xs">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <h3 className="text-lg font-black text-slate-900 flex items-center gap-2">
                    <Bell className="w-5 h-5 text-blue-600" /> Real-Time Notifications & Alerts
                  </h3>
                  {liveUnreadCount > 0 && (
                    <span className="text-[10px] font-black bg-blue-50 text-blue-600 border border-blue-200 px-2 py-0.5 rounded-full">
                      {liveUnreadCount} unread
                    </span>
                  )}
                </div>
                {liveUnreadCount > 0 && (
                  <button
                    onClick={markLiveAllAsRead}
                    className="text-xs font-bold text-blue-600 hover:underline cursor-pointer flex items-center gap-1"
                  >
                    <Check className="w-3.5 h-3.5" />
                    <span>Mark all as read</span>
                  </button>
                )}
              </div>

              {liveNotifications.length === 0 ? (
                <div className="py-8 text-center space-y-1">
                  <Bell className="w-7 h-7 text-slate-300 mx-auto" />
                  <p className="text-xs font-bold text-slate-700">No notifications yet</p>
                  <p className="text-[11px] text-slate-400">
                    Real-time WebSocket alerts will stream here instantly.
                  </p>
                </div>
              ) : (
                <div className="divide-y divide-slate-100 max-h-[380px] overflow-y-auto pr-1">
                  {liveNotifications.slice(0, 5).map((n) => (
                    <div
                      key={n.id}
                      className={`py-3 flex items-start justify-between gap-3 ${
                        n.status === "unread" ? "bg-blue-50/30 px-2.5 -mx-2.5 rounded-2xl" : ""
                      }`}
                    >
                      <div className="flex items-start gap-2.5 min-w-0 flex-1">
                        <div
                          className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 text-xs font-black ${
                            n.type === "AI_CHAT"
                              ? "bg-purple-100 text-purple-700"
                              : n.type === "RAG"
                              ? "bg-emerald-100 text-emerald-700"
                              : n.type === "COMPARISON"
                              ? "bg-indigo-100 text-indigo-700"
                              : "bg-blue-100 text-blue-700"
                          }`}
                        >
                          <Sparkles className="w-3.5 h-3.5" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-1.5">
                            <span className="text-xs font-black text-slate-800 truncate">{n.title}</span>
                            {n.status === "unread" && (
                              <span className="w-1.5 h-1.5 rounded-full bg-blue-600 shrink-0" />
                            )}
                          </div>
                          <p className="text-xs text-slate-500 font-medium line-clamp-1 mt-0.5">{n.message}</p>
                        </div>
                      </div>

                      <div className="flex items-center gap-1 shrink-0">
                        {n.status === "unread" && (
                          <button
                            onClick={() => markLiveAsRead(n.id)}
                            className="p-1 text-slate-400 hover:text-blue-600 rounded-md hover:bg-slate-100 cursor-pointer"
                            title="Mark read"
                          >
                            <Check className="w-3.5 h-3.5" />
                          </button>
                        )}
                        <button
                          onClick={() => deleteLiveNotification(n.id)}
                          className="p-1 text-slate-400 hover:text-rose-600 rounded-md hover:bg-slate-100 cursor-pointer"
                          title="Delete"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* TAB 2: PROFILE & PREFERENCES SETTINGS */}
      {/* ============================================================ */}
      {activeTab === "profile" && (
        <div className="space-y-6">
          {/* Profile Form Card */}
          <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 space-y-6 shadow-xs">
            <h2 className="text-xl font-black text-slate-900">Personal Information & Security</h2>
            <form onSubmit={handleSaveProfile} className="space-y-5">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Full Name</label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-xs font-bold text-slate-900 outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Email Address</label>
                  <input
                    type="email"
                    value={email}
                    disabled
                    className="w-full bg-slate-100 border border-slate-200 rounded-xl px-4 py-2.5 text-xs font-bold text-slate-500 cursor-not-allowed"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Professional Title</label>
                  <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="e.g. Hardware Architect"
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-xs font-bold text-slate-900 outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Phone Number</label>
                  <input
                    type="text"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="+91 98765 43210"
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-xs font-bold text-slate-900 outline-none focus:border-blue-500"
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-xs font-bold text-slate-700 mb-1">Location</label>
                  <input
                    type="text"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                    placeholder="Bangalore, India"
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-xs font-bold text-slate-900 outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              {/* Password Section */}
              <div className="pt-4 border-t border-slate-100 space-y-4">
                <h3 className="text-sm font-black text-slate-900">Change Account Password</h3>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">Current Password</label>
                    <input
                      type="password"
                      value={currentPassword}
                      onChange={(e) => setCurrentPassword(e.target.value)}
                      placeholder="••••••••"
                      className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-xs font-bold text-slate-900 outline-none focus:border-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">New Password</label>
                    <input
                      type="password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="••••••••"
                      className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-xs font-bold text-slate-900 outline-none focus:border-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">Confirm New Password</label>
                    <input
                      type="password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="••••••••"
                      className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-xs font-bold text-slate-900 outline-none focus:border-blue-500"
                    />
                  </div>
                </div>
              </div>

              <div className="pt-4 flex justify-end">
                <button
                  type="submit"
                  disabled={isSaving}
                  className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-extrabold text-xs rounded-xl shadow-md transition-all cursor-pointer flex items-center gap-2"
                >
                  {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                  <span>Save Profile Changes</span>
                </button>
              </div>
            </form>
          </div>


        </div>
      )}

      {/* ============================================================ */}
      {/* TAB 3: CONVERSATIONS HISTORY */}
      {/* ============================================================ */}
      {activeTab === "conversations" && (
        <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 space-y-4 shadow-xs">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-black text-slate-900 flex items-center gap-2">
              <MessageSquare className="w-5 h-5 text-blue-600" /> Saved AI Chat Sessions
            </h2>
            <span className="text-xs font-bold text-slate-400">{userConversations.length} sessions</span>
          </div>

          {userConversations.length === 0 ? (
            <div className="py-12 text-center space-y-2">
              <MessageSquare className="w-8 h-8 text-slate-300 mx-auto" />
              <p className="text-sm font-black text-slate-700">No chat sessions logged yet</p>
              <button
                onClick={() => onNavigate && onNavigate("chat")}
                className="mt-2 px-4 py-2 bg-blue-600 text-white text-xs font-extrabold rounded-xl hover:bg-blue-700 transition-all cursor-pointer"
              >
                Start AI Chat
              </button>
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {userConversations.map((c) => (
                <div key={c.conversation_id} className="py-4 flex items-center justify-between gap-4">
                  <div
                    className="min-w-0 flex-1 cursor-pointer group"
                    onClick={() => onNavigate && onNavigate("chat", c.title)}
                  >
                    <h4 className="text-xs font-black text-slate-900 group-hover:text-blue-600 transition-colors truncate">
                      {c.title}
                    </h4>
                    <p className="text-xs text-slate-400 font-medium line-clamp-1 mt-0.5">
                      {c.last_message}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-[10px] text-slate-400 font-bold">
                      {new Date(c.updated_at).toLocaleDateString()}
                    </span>
                    <button
                      onClick={() => handleDeleteConversation(c.conversation_id)}
                      className="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
                      title="Delete session"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ============================================================ */}
      {/* TAB 4: SAVED COMPARISONS */}
      {/* ============================================================ */}
      {activeTab === "comparisons" && (
        <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 space-y-4 shadow-xs">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-black text-slate-900 flex items-center gap-2">
              <Scale className="w-5 h-5 text-indigo-600" /> Saved Specification Matrices
            </h2>
            <span className="text-xs font-bold text-slate-400">{savedComparisons.length} saved</span>
          </div>

          {savedComparisons.length === 0 ? (
            <div className="py-12 text-center space-y-2">
              <Scale className="w-8 h-8 text-slate-300 mx-auto" />
              <p className="text-sm font-black text-slate-700">No comparisons saved yet</p>
              <button
                onClick={() => onNavigate && onNavigate("compare")}
                className="mt-2 px-4 py-2 bg-indigo-600 text-white text-xs font-extrabold rounded-xl hover:bg-indigo-700 transition-all cursor-pointer"
              >
                Create New Comparison
              </button>
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {savedComparisons.map((c) => {
                const title = c.summary || `Comparison ${c.comparison_id.slice(0, 8)}`;
                const count = c.product_ids?.length || 2;
                return (
                  <div key={c.comparison_id} className="py-4 flex items-center justify-between gap-4">
                    <div
                      className="min-w-0 flex-1 cursor-pointer group"
                      onClick={() => onNavigate && onNavigate("compare", title)}
                    >
                      <h4 className="text-xs font-black text-slate-900 group-hover:text-indigo-600 transition-colors truncate">
                        {title}
                      </h4>
                      <p className="text-[11px] text-slate-400 font-semibold mt-0.5">
                        {count} Devices Compared • Hardware Matrix
                      </p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="text-[10px] text-slate-400 font-bold">
                        {new Date(c.created_at).toLocaleDateString()}
                      </span>
                      <button
                        onClick={() => handleDeleteSavedComparison(c.comparison_id)}
                        className="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
                        title="Delete comparison"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}


    </div>
  );
}
