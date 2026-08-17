"use client";

import React, { useState, useEffect, Suspense, lazy } from "react";
import Navbar from "./components/Navbar";
import HomeView from "./components/HomeView";
import LoginView from "./components/LoginView";
import { Product, UserProfile } from "./types";
import { AuthProvider, useAuth } from "../context/AuthContext";
import { ComparisonProvider, useComparison } from "../context/ComparisonContext";
import { getFavorites } from "../services/api";

// Lazy-loaded heavy views — only downloaded when the user navigates to them
const CompareView = lazy(() => import("./components/CompareView"));
const AIChatView = lazy(() => import("./components/AIChatView"));
const DashboardView = lazy(() => import("./components/DashboardView"));
const DocumentsView = lazy(() => import("./components/DocumentsView"));
const AdminView = lazy(() => import("./components/AdminView"));
const WishlistView = lazy(() => import("./components/WishlistView"));

// Shared fallback for lazy-loaded views
function ViewSkeleton() {
  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="flex flex-col items-center gap-4">
        <div className="relative">
          <div className="w-12 h-12 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
          <div className="absolute inset-0 w-12 h-12 border-4 border-transparent border-b-indigo-400 rounded-full animate-spin" style={{ animationDirection: "reverse", animationDuration: "1.5s" }} />
        </div>
        <p className="text-sm text-slate-400 font-medium animate-pulse">Loading view...</p>
      </div>
    </div>
  );
}

function AppContent() {
  const { user, isAuthenticated, logout, updateUserProfile } = useAuth();
  const {
    selectedProducts,
    setSelectedProducts,
    removeProduct,
    isRestoring,
  } = useComparison();

  const [currentView, setCurrentView] = useState("home");
  const [dashboardTab, setDashboardTab] = useState<string>("overview");
  const [wishlist, setWishlist] = useState<Product[]>([]);
  const [notifications, setNotifications] = useState<string[]>([
    "Price Alert: ASUS Vivobook 16 OLED dropped by ₹2,000!",
    "New Article: 2026 Laptop Buyer's Guide published.",
  ]);
  const [initialChatQuery, setInitialChatQuery] = useState<string>("");

  // Load user favorites from backend when authenticated
  useEffect(() => {
    if (isAuthenticated) {
      getFavorites()
        .then((res) => {
          if (res?.items) {
            setWishlist(res.items);
          }
        })
        .catch(() => {});
    }
  }, [isAuthenticated]);

  const toggleWishlist = (product: Product) => {
    if (wishlist.some((p) => p.id === product.id)) {
      setWishlist(wishlist.filter((p) => p.id !== product.id));
    } else {
      setWishlist([...wishlist, product]);
      setNotifications((prev) => [`Added ${product.name} to Wishlist`, ...prev]);
    }
  };

  const handleSetPriceAlert = (product: Product, targetPrice: number) => {
    setNotifications((prev) => [
      `Price tracker active for ${product.name} at ₹${targetPrice.toLocaleString()}`,
      ...prev,
    ]);
  };

  const handleCompareFromHome = (selectedItems: Product[]) => {
    setSelectedProducts(selectedItems);
    setCurrentView("compare");
  };

  const handleRemoveFromCompare = (id: string) => {
    removeProduct(id);
  };

  const handleLogout = () => {
    logout();
    setCurrentView("login");
  };

  const handleLoginSuccess = (userObj: UserProfile) => {
    setCurrentView("home");
  };

  const handleLaunchChatWithQuery = (query: string) => {
    setInitialChatQuery(query);
    setCurrentView("chat");
  };

  const handleNavigate = (view: string, extraParam?: string) => {
    if (view === "chat" && extraParam) {
      setInitialChatQuery(extraParam);
    } else if (view === "dashboard" && extraParam) {
      setDashboardTab(extraParam);
    }
    setCurrentView(view);
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-[#0F172A] flex flex-col font-sans relative selection:bg-blue-100 selection:text-blue-900 bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(59,130,246,0.08),rgba(255,255,255,0))]">
      {/* Navigation Bar */}
      {currentView !== "login" && (
        <Navbar
          currentView={currentView}
          onNavigate={handleNavigate}
          shortlistedCount={selectedProducts.length}
          wishlistCount={wishlist.length}
          user={user}
          onLogout={handleLogout}
          notifications={notifications}
        />
      )}

      {/* Main View Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8">
        {currentView === "login" && (
          <LoginView onLoginSuccess={handleLoginSuccess} />
        )}

        {currentView === "home" && (
          <HomeView
            onCompare={handleCompareFromHome}
            shortlisted={selectedProducts}
            setShortlisted={setSelectedProducts}
            wishlist={wishlist}
            toggleWishlist={toggleWishlist}
            onSetPriceAlert={handleSetPriceAlert}
            onLaunchChatWithQuery={handleLaunchChatWithQuery}
          />
        )}

        {currentView === "compare" && (
          <Suspense fallback={<ViewSkeleton />}>
            <CompareView
              products={selectedProducts}
              onBack={() => setCurrentView("home")}
              onLaunchChat={() => setCurrentView("chat")}
              onRemove={handleRemoveFromCompare}
            />
          </Suspense>
        )}

        {currentView === "chat" && (
          <Suspense fallback={<ViewSkeleton />}>
            <AIChatView
              shortlisted={selectedProducts}
              onBack={() => setCurrentView("home")}
              initialQuery={initialChatQuery}
            />
          </Suspense>
        )}

        {currentView === "documents" && (
          <Suspense fallback={<ViewSkeleton />}>
            <DocumentsView onBack={() => setCurrentView("home")} />
          </Suspense>
        )}

        {currentView === "dashboard" && (
          <Suspense fallback={<ViewSkeleton />}>
            <DashboardView
              user={user}
              notifications={notifications}
              initialTab={dashboardTab}
              onNavigate={handleNavigate}
              onUpdateUser={updateUserProfile}
            />
          </Suspense>
        )}

        {currentView === "admin" && (
          <Suspense fallback={<ViewSkeleton />}>
            <AdminView onBack={() => setCurrentView("dashboard")} />
          </Suspense>
        )}

        {currentView === "wishlist" && (
          <Suspense fallback={<ViewSkeleton />}>
            <WishlistView
              wishlist={wishlist}
              toggleWishlist={toggleWishlist}
              onCompare={(prods: Product[]) => {
                setSelectedProducts(prods);
                setCurrentView("compare");
              }}
              onBack={() => setCurrentView("home")}
            />
          </Suspense>
        )}
      </main>
    </div>
  );
}

export default function Home() {
  return (
    <AuthProvider>
      <ComparisonProvider>
        <AppContent />
      </ComparisonProvider>
    </AuthProvider>
  );
}
