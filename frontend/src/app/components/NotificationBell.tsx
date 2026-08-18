"use client";

import React, { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Bell,
  CheckCheck,
  Trash2,
  Sparkles,
  FileText,
  Scale,
  Heart,
  ShieldCheck,
  Info,
  Check,
  X,
  Radio,
  ExternalLink,
} from "lucide-react";
import { useNotifications } from "../../context/NotificationContext";
import { AppNotification } from "../types";

interface NotificationBellProps {
  onNavigate?: (view: string, subTab?: string) => void;
}

export default function NotificationBell({ onNavigate }: NotificationBellProps) {
  const {
    notifications,
    unreadCount,
    isLoading,
    isConnected,
    markAsRead,
    markAllAsRead,
    deleteNotification,
    clearAll,
  } = useNotifications();

  const [isOpen, setIsOpen] = useState(false);
  const [filter, setFilter] = useState<"all" | "unread" | "ai" | "product">("all");
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  const filteredNotifications = notifications.filter((n) => {
    if (filter === "unread") return n.status === "unread";
    if (filter === "ai") return n.type === "AI_CHAT" || n.type === "RAG";
    if (filter === "product") return n.type === "PRODUCT" || n.type === "COMPARISON";
    return true;
  });

  const getNotificationIcon = (type: string) => {
    switch (type?.toUpperCase()) {
      case "AI_CHAT":
        return <Sparkles className="w-4 h-4 text-purple-600" />;
      case "RAG":
        return <FileText className="w-4 h-4 text-emerald-600" />;
      case "COMPARISON":
        return <Scale className="w-4 h-4 text-amber-600" />;
      case "PRODUCT":
        return <Heart className="w-4 h-4 text-rose-600" />;
      case "AUTH":
        return <ShieldCheck className="w-4 h-4 text-blue-600" />;
      default:
        return <Info className="w-4 h-4 text-slate-600" />;
    }
  };

  const getIconBg = (type: string) => {
    switch (type?.toUpperCase()) {
      case "AI_CHAT":
        return "bg-purple-100/80 border-purple-200/60";
      case "RAG":
        return "bg-emerald-100/80 border-emerald-200/60";
      case "COMPARISON":
        return "bg-amber-100/80 border-amber-200/60";
      case "PRODUCT":
        return "bg-rose-100/80 border-rose-200/60";
      case "AUTH":
        return "bg-blue-100/80 border-blue-200/60";
      default:
        return "bg-slate-100 border-slate-200";
    }
  };

  const formatRelativeTime = (dateStr: string) => {
    if (!dateStr) return "Just now";
    try {
      const now = new Date();
      const past = new Date(dateStr);
      const diffSec = Math.floor((now.getTime() - past.getTime()) / 1000);

      if (diffSec < 45) return "Just now";
      if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
      if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
      if (diffSec < 172800) return "Yesterday";
      return past.toLocaleDateString(undefined, { month: "short", day: "numeric" });
    } catch {
      return "Recently";
    }
  };

  const handleNotificationClick = (n: AppNotification) => {
    if (n.status === "unread") {
      markAsRead(n.id);
    }
    if (!onNavigate) return;

    if (n.type === "AI_CHAT") {
      onNavigate("chat");
    } else if (n.type === "RAG") {
      onNavigate("documents");
    } else if (n.type === "COMPARISON") {
      onNavigate("compare");
    } else if (n.type === "PRODUCT") {
      onNavigate("wishlist");
    } else if (n.type === "AUTH") {
      onNavigate("dashboard", "profile");
    }
    setIsOpen(false);
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell Trigger Button */}
      <button
        onClick={() => setIsOpen((prev) => !prev)}
        className={`relative p-2.5 rounded-2xl border transition-all duration-200 cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500/20 ${
          isOpen
            ? "bg-blue-50/80 border-blue-200 text-blue-700 shadow-sm"
            : "bg-slate-100 hover:bg-slate-200/70 border-slate-200 text-slate-700 hover:text-slate-900"
        }`}
        title="Notifications"
        aria-label={`Notifications (${unreadCount} unread)`}
      >
        <Bell className="w-4.5 h-4.5" />

        {/* Real-time Connection Indicator */}
        <span
          className={`absolute bottom-1 right-1 w-2 h-2 rounded-full border border-white ${
            isConnected ? "bg-emerald-500" : "bg-amber-400 animate-ping"
          }`}
          title={isConnected ? "Live real-time stream connected" : "Connecting..."}
        />

        {/* Unread Badge */}
        {unreadCount > 0 && (
          <span className="absolute -top-1.5 -right-1.5 min-w-5 h-5 px-1 bg-gradient-to-r from-blue-600 to-indigo-600 text-white text-[10px] font-black rounded-full flex items-center justify-center shadow-md ring-2 ring-white animate-pulse">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {/* Notifications Dropdown Panel */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 12, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.96 }}
            transition={{ duration: 0.16, ease: "easeOut" }}
            className="absolute right-0 mt-3 w-96 max-w-[calc(100vw-2rem)] bg-white rounded-3xl p-4 shadow-2xl border border-slate-200/90 z-50 space-y-3 backdrop-blur-xl"
          >
            {/* Header */}
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <span className="text-sm font-black text-slate-900 tracking-tight">Notifications</span>
                {unreadCount > 0 && (
                  <span className="text-[10px] font-extrabold bg-blue-50 text-blue-600 border border-blue-200/50 px-2 py-0.5 rounded-full">
                    {unreadCount} new
                  </span>
                )}
                {isConnected && (
                  <span className="flex items-center gap-1 text-[9px] font-bold text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded-full">
                    <Radio className="w-2.5 h-2.5 animate-pulse" /> Live
                  </span>
                )}
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-1">
                {unreadCount > 0 && (
                  <button
                    onClick={markAllAsRead}
                    className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-500 hover:text-blue-600 text-xs font-semibold flex items-center gap-1 transition-colors cursor-pointer"
                    title="Mark all as read"
                  >
                    <CheckCheck className="w-3.5 h-3.5" />
                    <span className="text-[11px] hidden sm:inline">Read all</span>
                  </button>
                )}
                {notifications.length > 0 && (
                  <button
                    onClick={clearAll}
                    className="p-1.5 rounded-lg hover:bg-rose-50 text-slate-400 hover:text-rose-600 text-xs transition-colors cursor-pointer"
                    title="Clear all notifications"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>

            {/* Filter Pills */}
            <div className="flex items-center gap-1.5 pb-1 overflow-x-auto no-scrollbar">
              {(
                [
                  { id: "all", label: "All" },
                  { id: "unread", label: `Unread (${unreadCount})` },
                  { id: "ai", label: "AI & RAG" },
                  { id: "product", label: "Products" },
                ] as const
              ).map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setFilter(tab.id)}
                  className={`text-[11px] font-bold px-2.5 py-1 rounded-full transition-all cursor-pointer whitespace-nowrap ${
                    filter === tab.id
                      ? "bg-slate-900 text-white shadow-xs"
                      : "bg-slate-100/80 hover:bg-slate-200/60 text-slate-600"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Notification List */}
            <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
              {isLoading && notifications.length === 0 ? (
                <div className="py-8 text-center space-y-2">
                  <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto" />
                  <p className="text-xs text-slate-400">Loading notifications...</p>
                </div>
              ) : filteredNotifications.length === 0 ? (
                <div className="py-10 text-center space-y-2">
                  <div className="w-10 h-10 rounded-2xl bg-slate-100 flex items-center justify-center mx-auto text-slate-400">
                    <Bell className="w-5 h-5" />
                  </div>
                  <p className="text-xs font-bold text-slate-700">All caught up!</p>
                  <p className="text-[11px] text-slate-400">
                    {filter === "unread" ? "No unread notifications" : "No recent activity or notifications"}
                  </p>
                </div>
              ) : (
                filteredNotifications.map((n) => (
                  <div
                    key={n.id}
                    onClick={() => handleNotificationClick(n)}
                    className={`group relative p-3 rounded-2xl border transition-all cursor-pointer flex items-start gap-3 ${
                      n.status === "unread"
                        ? "bg-blue-50/40 hover:bg-blue-50/80 border-blue-100/80 shadow-xs"
                        : "bg-slate-50/60 hover:bg-slate-100/80 border-slate-100"
                    }`}
                  >
                    {/* Type Icon */}
                    <div
                      className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 border ${getIconBg(
                        n.type
                      )}`}
                    >
                      {getNotificationIcon(n.type)}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0 pr-4">
                      <div className="flex items-center gap-1.5">
                        <p
                          className={`text-xs font-extrabold truncate ${
                            n.status === "unread" ? "text-slate-900" : "text-slate-700"
                          }`}
                        >
                          {n.title}
                        </p>
                        {n.status === "unread" && (
                          <span className="w-1.5 h-1.5 rounded-full bg-blue-600 shrink-0" />
                        )}
                      </div>
                      <p className="text-[11px] text-slate-600 font-medium line-clamp-2 mt-0.5 leading-relaxed">
                        {n.message}
                      </p>
                      <span className="text-[10px] text-slate-400 font-bold block mt-1">
                        {formatRelativeTime(n.created_at)}
                      </span>
                    </div>

                    {/* Hover Actions */}
                    <div className="absolute right-2 top-2 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity bg-white/90 rounded-lg p-0.5 border border-slate-200 shadow-xs">
                      {n.status === "unread" && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            markAsRead(n.id);
                          }}
                          className="p-1 text-slate-400 hover:text-blue-600 rounded hover:bg-slate-100"
                          title="Mark as read"
                        >
                          <Check className="w-3 h-3" />
                        </button>
                      )}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteNotification(n.id);
                        }}
                        className="p-1 text-slate-400 hover:text-rose-600 rounded hover:bg-slate-100"
                        title="Delete notification"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Footer */}
            {onNavigate && (
              <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
                <button
                  onClick={() => {
                    onNavigate("dashboard", "overview");
                    setIsOpen(false);
                  }}
                  className="w-full text-center py-1.5 text-xs font-bold text-blue-600 hover:text-blue-700 hover:bg-blue-50/50 rounded-xl transition-colors flex items-center justify-center gap-1 cursor-pointer"
                >
                  <span>View All in Dashboard</span>
                  <ExternalLink className="w-3 h-3" />
                </button>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
