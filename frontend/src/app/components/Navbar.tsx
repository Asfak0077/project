"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sparkles,
  Scale,
  Swords,
  MessageSquare,
  LayoutDashboard,
  BookOpen,
  LogOut,
  User as UserIcon,
  Heart,
  Bell,
  ChevronDown,
  FileText,
  ShieldCheck,
  Menu,
  X,
  Sliders,
  Settings,
  Layers,
} from "lucide-react";
import { UserProfile } from "../types";
import { getAssetUrl } from "../../services/api";
import NotificationBell from "./NotificationBell";

interface NavbarProps {
  currentView: string;
  onNavigate: (view: string, tab?: string) => void;
  shortlistedCount: number;
  wishlistCount: number;
  user: UserProfile | null;
  onLogout: () => void;
  notifications: string[];
}

export default function Navbar({
  currentView,
  onNavigate,
  shortlistedCount,
  wishlistCount,
  user,
  onLogout,
  notifications,
}: NavbarProps) {
  const [showUserDropdown, setShowUserDropdown] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navItems = [
    { id: "home", label: "Discover", icon: Sparkles },
    { id: "compare", label: "Compare", icon: Scale, badge: shortlistedCount },
    { id: "battle", label: "Battle", icon: Swords, badge: shortlistedCount >= 2 ? "⚡" : undefined, badgeColor: "bg-rose-600" },
    { id: "chat", label: "Ask AI", icon: MessageSquare },
    { id: "documents", label: "RAG Docs", icon: FileText },
    {
      id: "wishlist",
      label: "Wishlist",
      icon: Heart,
      badge: wishlistCount,
      badgeColor: "bg-rose-500",
    },
    { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
    ...(user?.isAdmin ? [{ id: "admin", label: "Admin", icon: ShieldCheck, badgeColor: "bg-purple-600" }] : []),
  ];

  const userAvatarUrl = getAssetUrl(user?.avatar);

  return (
    <header className="sticky top-0 z-50 bg-white/95 backdrop-blur-md border-b border-slate-200 shadow-[0_2px_15px_-3px_rgba(0,0,0,0.04)] transition-all">
      {/* Click-outside Backdrop */}
      {showUserDropdown && (
        <div
          onClick={() => {
            setShowUserDropdown(false);
          }}
          className="fixed inset-0 z-40 bg-transparent"
        />
      )}

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-18 flex items-center justify-between relative z-50">
        {/* Brand Logo */}
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => onNavigate("home")}
          className="flex items-center gap-3 text-left focus:outline-none group cursor-pointer"
        >
          <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-blue-600 via-cyan-600 to-indigo-600 flex items-center justify-center text-white shadow-lg shadow-blue-500/25 group-hover:shadow-blue-500/40 transition-shadow">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <div className="font-extrabold text-xl text-slate-900 tracking-tight leading-none flex items-center gap-1">
              Versus<span className="text-blue-600">AI</span>
            </div>
            <div className="text-[10px] font-extrabold text-slate-400 tracking-widest uppercase mt-1">
              RAG Spec Engine
            </div>
          </div>
        </motion.button>

        {/* Desktop & Tablet Navigation */}
        <nav className="hidden md:flex items-center gap-1 bg-slate-100/90 p-1.5 rounded-2xl border border-slate-200/90 shadow-inner">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentView === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onNavigate(item.id)}
                className={`relative px-3.5 py-2 rounded-xl text-xs font-extrabold transition-all flex items-center gap-2 cursor-pointer ${
                  isActive
                    ? "bg-white text-blue-600 shadow-sm border border-slate-200/80"
                    : "text-slate-600 hover:text-slate-900 hover:bg-white/60"
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? "text-blue-600" : "text-slate-500"}`} />
                <span>{item.label}</span>
                {Boolean(item.badge) && (
                  <span
                    className={`ml-1 px-1.5 py-0.5 rounded-full text-[10px] font-black text-white ${
                      item.badgeColor || "bg-blue-600"
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Right Actions: Notifications & User Profile */}
        <div className="flex items-center gap-3">
          {/* Real-time Notifications Bell */}
          <NotificationBell onNavigate={onNavigate} />

          {/* User Profile Dropdown or Sign In */}
          {user ? (
            <div className="relative">
              <button
                onClick={() => {
                  setShowUserDropdown(!showUserDropdown);
                }}
                className="flex items-center gap-2.5 p-1.5 pr-3 rounded-2xl bg-slate-100 hover:bg-slate-200/70 border border-slate-200 transition-all cursor-pointer"
              >
                <div className="w-8 h-8 rounded-xl overflow-hidden bg-slate-200 border border-slate-300 shrink-0">
                  <img
                    src={userAvatarUrl}
                    alt={user.name}
                    className="w-full h-full object-cover"
                  />
                </div>
                <div className="hidden sm:block text-left">
                  <div className="text-xs font-extrabold text-slate-900 leading-tight truncate max-w-[110px]">{user.name}</div>
                  <div className="text-[10px] font-bold text-blue-600 capitalize">{user.role || (user.isAdmin ? "Admin" : "User")}</div>
                </div>
                <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
              </button>

              {/* User Dropdown Panel */}
              <AnimatePresence>
                {showUserDropdown && (
                  <motion.div
                    initial={{ opacity: 0, y: 10, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 10, scale: 0.95 }}
                    className="absolute right-0 mt-3 w-60 bg-white rounded-3xl p-3 shadow-2xl border border-slate-200 z-50 space-y-1.5"
                  >
                    {/* User header inside dropdown */}
                    <div className="px-3 py-2 border-b border-slate-100 flex items-center gap-2.5 mb-1">
                      <div className="w-9 h-9 rounded-xl overflow-hidden bg-slate-100 border border-slate-200 shrink-0">
                        <img src={userAvatarUrl} alt={user.name} className="w-full h-full object-cover" />
                      </div>
                      <div className="min-w-0">
                        <div className="text-xs font-bold text-slate-900 truncate">{user.name}</div>
                        <div className="text-[10px] text-slate-400 truncate">{user.email}</div>
                      </div>
                    </div>

                    <button
                      onClick={() => {
                        onNavigate("dashboard", "profile");
                        setShowUserDropdown(false);
                      }}
                      className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-bold text-slate-700 hover:bg-slate-50 transition-colors cursor-pointer"
                    >
                      <UserIcon className="w-4 h-4 text-indigo-600" /> Edit Profile & Avatar
                    </button>

                    {user.isAdmin && (
                      <button
                        onClick={() => {
                          onNavigate("admin");
                          setShowUserDropdown(false);
                        }}
                        className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-bold text-purple-700 hover:bg-purple-50 transition-colors cursor-pointer"
                      >
                        <ShieldCheck className="w-4 h-4 text-purple-600" /> Admin Control Panel
                      </button>
                    )}

                    <div className="border-t border-slate-100 my-1" />

                    <button
                      onClick={() => {
                        onLogout();
                        setShowUserDropdown(false);
                      }}
                      className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-bold text-rose-600 hover:bg-rose-50 transition-colors cursor-pointer"
                    >
                      <LogOut className="w-4 h-4" /> Sign Out
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          ) : (
            <button
              onClick={() => onNavigate("login")}
              className="px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl text-xs font-extrabold shadow-md shadow-blue-500/20 transition-all cursor-pointer"
            >
              Sign In
            </button>
          )}

          {/* Mobile Menu Hamburger Toggle */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-2.5 rounded-2xl bg-slate-100 text-slate-700 border border-slate-200"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer Menu */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="md:hidden border-t border-slate-200 bg-white p-4 space-y-2"
          >
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.id}
                  onClick={() => {
                    onNavigate(item.id);
                    setMobileMenuOpen(false);
                  }}
                  className={`w-full flex items-center justify-between p-3 rounded-xl text-xs font-bold ${
                    currentView === item.id ? "bg-blue-50 text-blue-600" : "text-slate-700 hover:bg-slate-50"
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <Icon className="w-4 h-4" />
                    <span>{item.label}</span>
                  </div>
                  {Boolean(item.badge) && (
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-black bg-blue-600 text-white">
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
