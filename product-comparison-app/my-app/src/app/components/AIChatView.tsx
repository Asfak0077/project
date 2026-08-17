"use client";

import React, { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Product } from "../types";
import {
  Send,
  Bot,
  User,
  ArrowLeft,
  Sparkles,
  FileDown,
  Info,
  Copy,
  Check,
  Loader2,
  ExternalLink,
  Zap,
  FileText,
  Shield,
  Database,
  Layers,
  Cpu,
  HardDrive,
  BatteryCharging,
  AlertCircle,
  BarChart3,
  Flame,
  History,
  Plus,
  Trash2,
  Clock,
  X,
  MessageSquare,
  Terminal,
  Code2,
  ChevronDown,
  ChevronUp,
  Bug,
} from "lucide-react";
import {
  sendChatMessage,
  getUserConversations,
  deleteUserConversation,
  UserConversationSummary,
  RecommendedItem,
  SourceCitation,
} from "../../services/api";
import { useComparison } from "../../context/ComparisonContext";
import { getProductImage, formatRamDisplay } from "../../utils/imageHelper";

// ---------------------------------------------------------------------------
// Markdown Renderer (lightweight, no dependencies)
// ---------------------------------------------------------------------------

function renderMarkdown(text: string): React.ReactNode[] {
  const lines = text.split("\n");
  const elements: React.ReactNode[] = [];
  let inTable = false;
  let tableRows: string[][] = [];
  let tableHeader: string[] = [];

  const flushTable = () => {
    if (tableHeader.length > 0 || tableRows.length > 0) {
      elements.push(
        <div key={`table-${elements.length}`} className="overflow-x-auto my-3">
          <table className="w-full text-xs border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
            {tableHeader.length > 0 && (
              <thead>
                <tr className="bg-slate-100/80">
                  {tableHeader.map((h, i) => (
                    <th key={i} className="px-3 py-2.5 text-left font-bold text-slate-800 border-b border-slate-200">
                      {renderInline(h.trim())}
                    </th>
                  ))}
                </tr>
              </thead>
            )}
            <tbody>
              {tableRows.map((row, ri) => (
                <tr key={ri} className={ri % 2 === 0 ? "bg-white" : "bg-slate-50/50"}>
                  {row.map((cell, ci) => (
                    <td key={ci} className="px-3 py-2 text-slate-700 border-b border-slate-100 font-medium">
                      {renderInline(cell.trim())}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }
    tableRows = [];
    tableHeader = [];
    inTable = false;
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    // Table row detection
    if (trimmed.startsWith("|") && trimmed.endsWith("|")) {
      const cells = trimmed.split("|").filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);
      // Separator row (|---|---|)
      if (cells.every((c) => /^[\s\-:]+$/.test(c))) {
        inTable = true;
        continue;
      }
      if (!inTable && tableHeader.length === 0) {
        tableHeader = cells;
      } else {
        inTable = true;
        tableRows.push(cells);
      }
      continue;
    } else if (inTable) {
      flushTable();
    }

    // Heading ### / ## / #
    if (trimmed.startsWith("### ")) {
      elements.push(
        <h4 key={i} className="text-xs font-black text-slate-900 mt-3 mb-1 flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-blue-600 shrink-0" />
          {renderInline(trimmed.slice(4))}
        </h4>
      );
    } else if (trimmed.startsWith("## ")) {
      elements.push(
        <h3 key={i} className="text-sm font-black text-slate-900 mt-3 mb-1.5 flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-blue-600 shrink-0" />
          {renderInline(trimmed.slice(3))}
        </h3>
      );
    } else if (trimmed.startsWith("# ")) {
      elements.push(
        <h2 key={i} className="text-base font-black text-slate-900 mt-3 mb-2">
          {renderInline(trimmed.slice(2))}
        </h2>
      );
    }
    // Bullet points
    else if (trimmed.startsWith("• ") || trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      elements.push(
        <div key={i} className="flex items-start gap-2 ml-1 py-0.5">
          <span className="text-blue-600 mt-0.5 shrink-0 font-black">•</span>
          <span className="text-slate-700">{renderInline(trimmed.slice(2))}</span>
        </div>
      );
    }
    // Source citation
    else if (trimmed.startsWith("[Source:")) {
      elements.push(
        <span key={i} className="inline-flex items-center gap-1 text-[10px] font-bold text-blue-600 bg-blue-50/80 px-2.5 py-1 rounded-lg mt-1 border border-blue-100">
          <FileText className="w-3 h-3" />
          {trimmed}
        </span>
      );
    }
    // Empty line
    else if (trimmed === "") {
      elements.push(<div key={i} className="h-1.5" />);
    }
    // Regular paragraph
    else {
      elements.push(
        <p key={i} className="leading-relaxed text-slate-700">
          {renderInline(trimmed)}
        </p>
      );
    }
  }

  if (inTable || tableHeader.length > 0) {
    flushTable();
  }

  return elements;
}

function renderInline(text: string): React.ReactNode {
  const parts: React.ReactNode[] = [];
  let remaining = text;
  let keyIdx = 0;

  while (remaining.length > 0) {
    const boldMatch = remaining.match(/\*\*(.+?)\*\*/);
    if (boldMatch && boldMatch.index !== undefined) {
      if (boldMatch.index > 0) {
        parts.push(remaining.slice(0, boldMatch.index));
      }
      parts.push(
        <strong key={`b-${keyIdx++}`} className="font-bold text-slate-900">
          {boldMatch[1]}
        </strong>
      );
      remaining = remaining.slice(boldMatch.index + boldMatch[0].length);
      continue;
    }

    const codeMatch = remaining.match(/`([^`]+)`/);
    if (codeMatch && codeMatch.index !== undefined) {
      if (codeMatch.index > 0) {
        parts.push(remaining.slice(0, codeMatch.index));
      }
      parts.push(
        <code key={`c-${keyIdx++}`} className="bg-slate-100 text-slate-800 px-1.5 py-0.5 rounded text-[11px] font-mono border border-slate-200">
          {codeMatch[1]}
        </code>
      );
      remaining = remaining.slice(codeMatch.index + codeMatch[0].length);
      continue;
    }

    parts.push(remaining);
    break;
  }

  return parts.length === 1 ? parts[0] : <>{parts}</>;
}

// ---------------------------------------------------------------------------
// Helpers: Spec & Analysis Content Parsers
// ---------------------------------------------------------------------------

function parseSpecContent(content: string): { isSpec: boolean; key: string; value: string } {
  const trimmed = content.trim();
  const specMatch = trimmed.match(/^([A-Za-z\s]+):\s*(.+)$/);
  if (specMatch && !trimmed.includes("\n")) {
    const key = specMatch[1].trim();
    const value = specMatch[2].trim();
    const allowedKeys = [
      "ram", "memory", "price", "processor", "cpu", "chipset", "storage", "disk", "ssd", "hdd",
      "gpu", "graphics", "battery", "camera", "cameras", "display", "screen", "operating system",
      "os", "rating", "cooling", "warranty", "cellular", "5g", "stylus",
    ];
    if (allowedKeys.includes(key.toLowerCase())) {
      return { isSpec: true, key: key.toUpperCase(), value };
    }
  }
  return { isSpec: false, key: "", value: "" };
}

function parseAnalysisContent(content: string): {
  isAnalysis: boolean;
  product?: string;
  performance?: string;
  memory?: string;
  storage?: string;
  battery?: string;
} {
  const trimmed = content.trim();
  if (!trimmed.startsWith("## Product Analysis")) {
    return { isAnalysis: false };
  }

  // Single product analysis pattern
  if (!trimmed.includes("### Product")) {
    const getField = (field: string) => {
      const match = trimmed.match(new RegExp(`\\*\\*${field}:\\*\\*\\s*\\n?([^\\n*]+(?:\\n(?!\\*\\*)[^\\n*]+)*)`, "i"));
      return match ? match[1].trim() : undefined;
    };

    const product = getField("Product");
    const performance = getField("Performance");
    const memory = getField("Memory");
    const storage = getField("Storage");
    const battery = getField("Battery");

    if (product || performance || memory) {
      return {
        isAnalysis: true,
        product,
        performance,
        memory,
        storage,
        battery,
      };
    }
  }

  return { isAnalysis: false };
}

// ---------------------------------------------------------------------------
// Interfaces
// ---------------------------------------------------------------------------

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  products?: any[];
  recommendations?: RecommendedItem[];
  sources?: SourceCitation[];
  suggested_followups?: string[];
  confidence?: string;
  context_used?: string;
  show_recommendations?: boolean;
  show_comparison?: boolean;
  show_sources?: boolean;
  type?: string;
  debug_trace?: any;
  product?: any;
}

interface AIChatViewProps {
  onBack: () => void;
  shortlisted?: Product[];
  initialQuery?: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function AIChatView({ onBack, shortlisted: propShortlisted, initialQuery }: AIChatViewProps) {
  const {
    conversationId,
    selectedProducts: contextShortlisted,
    activeProduct,
    setActiveProduct,
    messages,
    addMessage,
    loadConversation,
    clearAllSessionData,
  } = useComparison();

  const shortlisted = propShortlisted && propShortlisted.length > 0 ? propShortlisted : contextShortlisted;

  const [input, setInput] = useState(initialQuery || "");
  const [isTyping, setIsTyping] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [showDebugMode, setShowDebugMode] = useState(false);
  const [expandedDebugIds, setExpandedDebugIds] = useState<Record<string, boolean>>({});
  const [conversations, setConversations] = useState<UserConversationSummary[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const fetchConversations = async () => {
    setLoadingHistory(true);
    try {
      const data = await getUserConversations();
      setConversations(data || []);
    } catch (err) {
      console.debug("Could not fetch conversations:", err);
    } finally {
      setLoadingHistory(false);
    }
  };

  const handleOpenHistory = () => {
    setShowHistoryModal(true);
    fetchConversations();
  };

  const handleSelectConv = async (cid: string) => {
    setShowHistoryModal(false);
    await loadConversation(cid);
  };

  const handleDeleteConv = async (e: React.MouseEvent, cid: string) => {
    e.stopPropagation();
    try {
      await deleteUserConversation(cid);
      setConversations((prev) => prev.filter((c) => c.conversation_id !== cid));
      if (cid === conversationId) {
        clearAllSessionData();
      }
    } catch (err) {
      console.error("Delete conversation error:", err);
    }
  };

  const handleNewChat = () => {
    clearAllSessionData();
  };

  useEffect(() => {
    if (initialQuery) {
      setInput(initialQuery);
    }
  }, [initialQuery]);

  const defaultGreeting: Message = useMemo(() => ({
    id: "greeting",
    role: "assistant" as const,
    content: shortlisted.length > 0
      ? `Hello! I'm your **VersusAI Product Intelligence Assistant**. I see you have **${shortlisted.length}** product(s) active in context. You can ask for specifications (e.g. \`ram\`, \`price\`), product explanations (e.g. \`explain product 1\`), or comparisons.`
      : "Hello! I am your **VersusAI Product Intelligence Assistant**. Ask me about laptop, smartphone, or tablet specifications, benchmarks, recommendations, or side-by-side comparisons.",
    timestamp: new Date(),
    suggested_followups: [
      "Best gaming laptop under ₹80,000",
      "Explain product 1",
      "Compare ASUS ROG and MSI Titan",
    ],
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }), [shortlisted.length]);

  const displayMessages = useMemo(() => messages.length > 0 ? messages : [defaultGreeting], [messages, defaultGreeting]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const handleSendMessage = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isTyping) return;

    const userQuery = input.trim();
    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: userQuery,
      timestamp: new Date(),
    };

    addMessage(userMessage);
    setInput("");
    setIsTyping(true);

    try {
      // Limit history to last 10 messages to reduce request payload size
      const recentMessages = displayMessages.slice(-10);
      const historyPayload = recentMessages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const contextProductsPayload = shortlisted.map((p, idx) => ({
        index: idx + 1,
        id: p.id,
        name: p.name,
      }));

      const res = await sendChatMessage({
        message: userQuery,
        history: historyPayload,
        shortlisted_ids: shortlisted.map((p) => p.id),
        context_products: contextProductsPayload,
        active_product_id: activeProduct ? activeProduct.id : (shortlisted.length === 1 ? shortlisted[0].id : undefined),
        session_id: conversationId,
        conversation_id: conversationId,
      });

      if (res.product) {
        setActiveProduct(res.product);
      }

      const isError = res.type === "error" || (res as any).success === false;
      const aiResponse: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: res.answer || res.message || "I couldn't complete the product analysis. Please try again.",
        timestamp: new Date(),
        products: res.products,
        recommendations: res.recommendations,
        sources: res.sources || [],
        suggested_followups: res.suggested_followups || [],
        confidence: res.confidence || "Database Verified",
        context_used: res.context_used || "database",
        show_recommendations: res.show_recommendations,
        show_comparison: res.show_comparison,
        show_sources: res.show_sources,
        type: res.type || (isError ? "error" : "general"),
        debug_trace: res.debug_trace,
      };

      addMessage(aiResponse);
    } catch (err: any) {
      console.error("Chat API Error:", err);
      const errorMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "I couldn't complete the product analysis. Please try again.",
        timestamp: new Date(),
        confidence: "low",
        context_used: "general",
        type: "error",
        suggested_followups: [
          "Tell me about ASUS ROG",
          "Explain product 1",
          "Compare ASUS and MSI",
        ],
      };
      addMessage(errorMsg);
    } finally {
      setIsTyping(false);
    }
  }, [input, isTyping, displayMessages, shortlisted, activeProduct, conversationId, addMessage, setActiveProduct]);

  const handleCopy = (id: string, content: string) => {
    navigator.clipboard.writeText(content.replace(/\*\*/g, "").replace(/## /g, ""));
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleExportChat = () => {
    const text = messages
      .map((m) => `[${m.role.toUpperCase()}] ${new Date(m.timestamp).toLocaleTimeString()}:\n${m.content}\n`)
      .join("\n-------------------\n\n");
    const blob = new Blob([text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `versus-ai-chat-${new Date().toISOString().slice(0, 10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleFollowupClick = (question: string) => {
    setInput(question);
  };

  const suggestedQuestions = [
    "Explain product 1",
    "Explain product 1 and 2",
    "What is the RAM and battery of product 1?",
    "Best price-to-performance laptop under ₹80,000",
  ];

  return (
    <div className="py-4 sm:py-6 h-[calc(100vh-80px)] flex flex-col max-w-7xl mx-auto w-full px-2 sm:px-4">
      {/* Top Glass Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between bg-white/90 backdrop-blur-md border border-slate-200/80 rounded-t-3xl p-4 gap-4 shrink-0 shadow-xs">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="p-2.5 text-slate-500 hover:text-slate-900 bg-slate-100 hover:bg-slate-200/80 rounded-xl transition-all cursor-pointer shadow-2xs"
            title="Back to Discovery"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-blue-600 via-indigo-600 to-purple-600 flex items-center justify-center text-white shadow-md shadow-blue-500/25">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base sm:text-lg font-black text-slate-900 flex items-center gap-2">
                VersusAI Intelligence Assistant <Sparkles className="w-4 h-4 text-blue-600" />
              </h2>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
                <p className="text-[11px] font-bold text-slate-500">Authoritative MySQL & RAG Spec Pipeline</p>
              </div>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowDebugMode(!showDebugMode)}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-bold border transition-all cursor-pointer shadow-2xs ${
              showDebugMode
                ? "bg-amber-500 text-white border-amber-600 shadow-amber-500/20"
                : "bg-slate-100 hover:bg-slate-200/80 text-slate-700 border-slate-200"
            }`}
            title="Toggle Developer Pipeline Trace Panel"
          >
            <Bug className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Debug {showDebugMode ? "ON" : "OFF"}</span>
          </button>
          <button
            onClick={handleNewChat}
            className="flex items-center gap-1.5 px-3 py-2 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-xl text-xs font-bold border border-blue-200 transition-all cursor-pointer shadow-2xs"
            title="Start a fresh conversation"
          >
            <Plus className="w-3.5 h-3.5" /> New Chat
          </button>
          <button
            onClick={handleOpenHistory}
            className="flex items-center gap-1.5 px-3 py-2 bg-slate-100 hover:bg-slate-200/80 text-slate-700 rounded-xl text-xs font-bold border border-slate-200 transition-all cursor-pointer shadow-2xs"
            title="View past conversations stored in MySQL"
          >
            <History className="w-3.5 h-3.5 text-indigo-600" /> My Conversations
          </button>
          <button
            onClick={handleExportChat}
            className="flex items-center gap-1.5 px-3 py-2 bg-slate-100/90 hover:bg-slate-200/90 text-slate-700 rounded-xl text-xs font-bold border border-slate-200 transition-all cursor-pointer shadow-2xs"
          >
            <FileDown className="w-3.5 h-3.5 text-blue-600" /> Export Chat
          </button>
        </div>
      </div>

      <div className="flex flex-col lg:flex-row flex-1 overflow-hidden bg-white/80 backdrop-blur-md border border-slate-200/80 rounded-b-3xl border-t-0 shadow-lg">
        {/* Context Sidebar */}
        <div className="hidden lg:block w-80 bg-slate-50/70 border-r border-slate-200/80 p-4 sm:p-5 overflow-y-auto shrink-0 space-y-4">
          <div className="text-[11px] font-extrabold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
            <Info className="w-3.5 h-3.5 text-blue-600" /> Active Context Window
          </div>

          {shortlisted.length === 0 ? (
            <div className="text-xs text-slate-500 font-medium text-center py-8 bg-white/90 rounded-2xl border border-dashed border-slate-200 p-4">
              No products shortlisted yet. Select products in Discover to view direct side-by-side analysis.
            </div>
          ) : (
            <div className="space-y-2.5">
              {shortlisted.map((p, idx) => {
                const displayName = p.name.toLowerCase().startsWith(p.brand.toLowerCase() + " ")
                  ? p.name
                  : `${p.brand} ${p.name}`;
                const imgSrc = getProductImage(p);
                const ramDisplay = formatRamDisplay(p.ram);
                return (
                  <div
                    key={p.id}
                    className="bg-white/95 border border-slate-200/90 rounded-2xl p-3 shadow-2xs space-y-2 hover:border-blue-300 hover:shadow-xs transition-all flex items-center gap-3"
                  >
                    <div className="w-12 h-12 rounded-xl bg-slate-100 border border-slate-200 overflow-hidden shrink-0">
                      <img
                        src={imgSrc}
                        alt={displayName}
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          (e.target as HTMLImageElement).src = getProductImage({ category: p.category });
                        }}
                      />
                    </div>
                    <div className="min-w-0 flex-1 space-y-0.5">
                      <div className="flex items-center justify-between gap-1">
                        <span className="text-[10px] font-black text-blue-600 uppercase tracking-wider">
                          Product {idx + 1} • {p.brand}
                        </span>
                        <span className="text-[10px] font-black text-slate-600">⭐ {p.score || 85}/100</span>
                      </div>
                      <div className="text-xs font-bold text-slate-900 truncate" title={displayName}>
                        {displayName}
                      </div>
                      <div className="flex items-center justify-between text-[11px] text-slate-500 font-bold">
                        <span className="text-slate-900 font-black">₹{Number(p.price).toLocaleString()}</span>
                        <span>{ramDisplay}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Quick Prompts */}
          <div className="pt-2">
            <div className="text-[11px] font-extrabold text-slate-500 uppercase tracking-wider mb-2">
              Suggested Questions
            </div>
            <div className="space-y-1.5">
              {suggestedQuestions.map((q, i) => (
                <button
                  key={i}
                  onClick={() => setInput(q)}
                  className="w-full text-left p-2 bg-white/90 hover:bg-blue-50 border border-slate-200 hover:border-blue-300 rounded-xl text-xs font-semibold text-slate-700 hover:text-blue-700 transition-all cursor-pointer shadow-2xs"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Chat Main Area */}
        <div className="flex-1 flex flex-col h-full bg-slate-50/40 overflow-hidden">
          {/* Messages Scroll Area */}
          <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
            {displayMessages.map((msg) => {
              const isUser = msg.role === "user";
              const specData = !isUser ? parseSpecContent(msg.content) : { isSpec: false, key: "", value: "" };
              const analysisData = !isUser ? parseAnalysisContent(msg.content) : { isAnalysis: false };

              return (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`flex gap-3 max-w-3xl ${isUser ? "ml-auto flex-row-reverse" : "mr-auto"}`}
                >
                  <div
                    className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 shadow-xs ${
                      isUser
                        ? "bg-slate-800 text-white"
                        : "bg-gradient-to-tr from-blue-600 to-indigo-600 text-white"
                    }`}
                  >
                    {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                  </div>

                  <div
                    className={`rounded-2xl p-4 sm:p-5 shadow-2xs space-y-3 ${
                      isUser
                        ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-medium"
                        : "bg-white border border-slate-200/90 text-slate-800"
                    }`}
                  >
                    {/* Message Body */}
                    {specData.isSpec ? (
                      <div className="flex items-center gap-2 text-sm font-black text-slate-900 bg-blue-50/70 border border-blue-200/70 px-3.5 py-2.5 rounded-xl shadow-2xs">
                        <span className="text-blue-600 uppercase tracking-wide">{specData.key}:</span>
                        <span>{specData.value}</span>
                      </div>
                    ) : analysisData.isAnalysis ? (
                      <div className="space-y-3">
                        <div className="text-sm font-black text-slate-900 flex items-center gap-2 pb-2 border-b border-slate-100">
                          <BarChart3 className="w-4 h-4 text-blue-600" />
                          <span>Hardware Analysis: {analysisData.product}</span>
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                          {analysisData.performance && (
                            <div className="bg-slate-50 border border-slate-200/80 rounded-xl p-2.5">
                              <div className="font-bold text-blue-600 flex items-center gap-1 mb-0.5">
                                <Cpu className="w-3.5 h-3.5" /> Performance
                              </div>
                              <div className="text-slate-700">{analysisData.performance}</div>
                            </div>
                          )}
                          {analysisData.memory && (
                            <div className="bg-slate-50 border border-slate-200/80 rounded-xl p-2.5">
                              <div className="font-bold text-indigo-600 flex items-center gap-1 mb-0.5">
                                <Zap className="w-3.5 h-3.5" /> Memory
                              </div>
                              <div className="text-slate-700">{analysisData.memory}</div>
                            </div>
                          )}
                          {analysisData.storage && (
                            <div className="bg-slate-50 border border-slate-200/80 rounded-xl p-2.5">
                              <div className="font-bold text-amber-600 flex items-center gap-1 mb-0.5">
                                <HardDrive className="w-3.5 h-3.5" /> Storage
                              </div>
                              <div className="text-slate-700">{analysisData.storage}</div>
                            </div>
                          )}
                          {analysisData.battery && (
                            <div className="bg-slate-50 border border-slate-200/80 rounded-xl p-2.5">
                              <div className="font-bold text-emerald-600 flex items-center gap-1 mb-0.5">
                                <BatteryCharging className="w-3.5 h-3.5" /> Battery
                              </div>
                              <div className="text-slate-700">{analysisData.battery}</div>
                            </div>
                          )}
                        </div>
                      </div>
                    ) : (
                      <div className="text-xs sm:text-sm leading-relaxed space-y-2">
                        {renderMarkdown(msg.content)}
                      </div>
                    )}

                    {/* Footer Actions / Citations */}
                    {!isUser && (
                      <div className="pt-2 border-t border-slate-100 flex flex-col gap-2">
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            {msg.context_used === "documents" ? (
                              <span className="inline-flex items-center gap-1 font-bold text-purple-700 bg-purple-50 px-2 py-0.5 rounded-lg border border-purple-200/60 text-[10px]">
                                <Check className="w-3 h-3 text-purple-600" /> RAG Verified
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-lg border border-emerald-200/60 text-[10px]">
                                <Check className="w-3 h-3 text-emerald-600" /> Database Verified
                              </span>
                            )}
                            {msg.debug_trace && (
                              <button
                                onClick={() =>
                                  setExpandedDebugIds((prev) => ({
                                    ...prev,
                                    [msg.id]: !prev[msg.id],
                                  }))
                                }
                                className="inline-flex items-center gap-1 font-bold text-amber-700 bg-amber-50 hover:bg-amber-100 px-2 py-0.5 rounded-lg border border-amber-200/70 text-[10px] cursor-pointer transition-colors"
                              >
                                <Code2 className="w-3 h-3 text-amber-600" /> Trace
                                {expandedDebugIds[msg.id] || showDebugMode ? (
                                  <ChevronUp className="w-2.5 h-2.5" />
                                ) : (
                                  <ChevronDown className="w-2.5 h-2.5" />
                                )}
                              </button>
                            )}
                          </div>
                          <button
                            onClick={() => handleCopy(msg.id, msg.content)}
                            className="text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
                            title="Copy Answer"
                          >
                            {copiedId === msg.id ? (
                              <Check className="w-3.5 h-3.5 text-emerald-600" />
                            ) : (
                              <Copy className="w-3.5 h-3.5" />
                            )}
                          </button>
                        </div>

                        {/* Collapsible Developer Pipeline Trace */}
                        {msg.debug_trace && (expandedDebugIds[msg.id] || showDebugMode) && (
                          <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: "auto" }}
                            exit={{ opacity: 0, height: 0 }}
                            className="mt-2 p-3 bg-slate-900 text-slate-200 rounded-xl text-[11px] font-mono space-y-1.5 border border-slate-800 shadow-inner"
                          >
                            <div className="flex items-center justify-between text-amber-400 font-bold border-b border-slate-800 pb-1 text-[10px]">
                              <span className="flex items-center gap-1">
                                <Terminal className="w-3 h-3 text-amber-400" /> Developer Pipeline Trace
                              </span>
                              <span className="text-slate-400">
                                Route: {msg.debug_trace.route_selected || "DIRECT_MYSQL"}
                              </span>
                            </div>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-3 gap-y-1 pt-1">
                              <div>
                                <span className="text-slate-400">User Query:</span>{" "}
                                <span className="text-white font-semibold">
                                  {msg.debug_trace.raw_query || msg.debug_trace.user_query}
                                </span>
                              </div>
                              <div>
                                <span className="text-slate-400">Detected Intent:</span>{" "}
                                <span className="text-emerald-400 font-semibold">
                                  {msg.debug_trace.detected_intent || msg.debug_trace.intent}
                                </span>
                              </div>
                              <div>
                                <span className="text-slate-400">Target Field:</span>{" "}
                                <span className="text-indigo-300 font-semibold">
                                  {msg.debug_trace.spec_field || msg.debug_trace.field || "N/A"}
                                </span>
                              </div>
                              <div>
                                <span className="text-slate-400">Target Index:</span>{" "}
                                <span className="text-amber-300 font-semibold">
                                  {msg.debug_trace.target_product_index != null
                                    ? `Product #${msg.debug_trace.target_product_index}`
                                    : "Auto-Selected"}
                                </span>
                              </div>
                              <div className="sm:col-span-2">
                                <span className="text-slate-400">Resolved Product:</span>{" "}
                                <span className="text-blue-300 font-semibold">
                                  {msg.debug_trace.resolved_product ||
                                    (msg.product ? `${msg.product.brand} ${msg.product.name}` : "Context Active")}
                                  {msg.debug_trace.resolved_product_id
                                    ? ` (ID: ${msg.debug_trace.resolved_product_id})`
                                    : ""}
                                </span>
                              </div>
                              <div className="sm:col-span-2">
                                <span className="text-slate-400">Result / Ground Truth:</span>{" "}
                                <span className="text-emerald-300">
                                  {msg.debug_trace.database_result ||
                                    msg.debug_trace.rag_result ||
                                    msg.debug_trace.final_answer ||
                                    "Verified Ground Truth"}
                                </span>
                              </div>
                              {msg.debug_trace.timing && (
                                <div className="sm:col-span-2 mt-1 pt-1.5 border-t border-slate-800">
                                  <span className="text-amber-400 font-bold text-[10px]">⚡ Performance Timing</span>
                                  <div className="flex flex-wrap gap-3 mt-1">
                                    <span className="text-cyan-300">
                                      NLP: <strong>{msg.debug_trace.timing.nlp_ms}ms</strong>
                                    </span>
                                    <span className="text-purple-300">
                                      Resolve: <strong>{msg.debug_trace.timing.resolve_ms}ms</strong>
                                    </span>
                                    <span className="text-green-300">
                                      Route: <strong>{msg.debug_trace.timing.route_ms}ms</strong>
                                    </span>
                                    <span className="text-slate-300">
                                      Storage: <strong>{msg.debug_trace.timing.storage_ms}ms</strong>
                                    </span>
                                    <span className="text-amber-300 font-bold">
                                      Total: {msg.debug_trace.timing.total_ms}ms
                                    </span>
                                  </div>
                                </div>
                              )}
                              {msg.debug_trace.cache_stats && (
                                <div className="sm:col-span-2 text-cyan-400">
                                  <span className="text-slate-400">Cache:</span>{" "}
                                  ⚡ HIT — {msg.debug_trace.cache_stats.hit_rate}% hit rate ({msg.debug_trace.cache_stats.size} entries)
                                </div>
                              )}
                            </div>
                          </motion.div>
                        )}
                      </div>
                    )}
                  </div>
                </motion.div>
              );
            })}
            {isTyping && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex gap-3 items-start"
              >
                <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-md flex-shrink-0">
                  <Bot className="w-4 h-4 text-white" />
                </div>
                <div className="bg-gradient-to-r from-slate-50 to-blue-50/60 border border-slate-200/60 px-5 py-3.5 rounded-2xl shadow-sm">
                  <div className="flex items-center gap-2.5">
                    <div className="flex gap-1">
                      <span className="w-2 h-2 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: "0ms" }} />
                      <span className="w-2 h-2 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: "150ms" }} />
                      <span className="w-2 h-2 rounded-full bg-blue-300 animate-bounce" style={{ animationDelay: "300ms" }} />
                    </div>
                    <span className="text-xs font-medium text-slate-500 animate-pulse">AI Analyzing...</span>
                  </div>
                </div>
              </motion.div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Chat Input Bar */}
          <form onSubmit={handleSendMessage} className="p-3.5 sm:p-4 bg-white/90 backdrop-blur-md border-t border-slate-200/80 flex items-center gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a technical spec (e.g. 'ram', 'price'), 'explain product 1', or 'compare 1 and 2'..."
              className="flex-1 bg-slate-50/90 border border-slate-200/90 rounded-2xl px-4 py-3 text-xs sm:text-sm font-semibold text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-all shadow-2xs"
            />
            <button
              type="submit"
              disabled={!input.trim() || isTyping}
              className="p-3 sm:px-5 sm:py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-2xl shadow-md shadow-blue-500/20 disabled:opacity-50 transition-all cursor-pointer flex items-center gap-2 font-bold text-xs sm:text-sm"
            >
              <Send className="w-4 h-4" />
              <span className="hidden sm:inline">Send</span>
            </button>
          </form>
        </div>
      </div>

      {/* My Conversations Modal */}
      <AnimatePresence>
        {showHistoryModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 10 }}
              className="bg-white rounded-3xl max-w-xl w-full p-6 shadow-2xl border border-slate-200 space-y-4 max-h-[85vh] flex flex-col"
            >
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div className="flex items-center gap-2.5">
                  <div className="w-9 h-9 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center font-bold">
                    <History className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-base font-black text-slate-900">My AI Conversations</h3>
                    <p className="text-xs text-slate-500 font-medium">Persisted in MySQL Database</p>
                  </div>
                </div>
                <button
                  onClick={() => setShowHistoryModal(false)}
                  className="p-2 text-slate-400 hover:text-slate-700 rounded-xl hover:bg-slate-100 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="flex-1 overflow-y-auto space-y-2.5 pr-1">
                {loadingHistory ? (
                  <div className="py-12 flex flex-col items-center justify-center gap-2 text-slate-500 text-xs font-bold">
                    <Loader2 className="w-5 h-5 animate-spin text-blue-600" />
                    Loading your past conversations from database...
                  </div>
                ) : conversations.length === 0 ? (
                  <div className="py-12 text-center text-xs text-slate-500 font-medium bg-slate-50 rounded-2xl p-6 border border-dashed border-slate-200">
                    <MessageSquare className="w-8 h-8 mx-auto text-slate-300 mb-2" />
                    No previous conversations found. Start chatting to save conversations to your account.
                  </div>
                ) : (
                  conversations.map((c) => (
                    <div
                      key={c.conversation_id}
                      onClick={() => handleSelectConv(c.conversation_id)}
                      className={`p-3.5 rounded-2xl border transition-all cursor-pointer flex items-start justify-between gap-3 ${
                        c.conversation_id === conversationId
                          ? "bg-blue-50/70 border-blue-300 shadow-xs"
                          : "bg-slate-50/70 border-slate-200 hover:bg-blue-50/40 hover:border-blue-200"
                      }`}
                    >
                      <div className="min-w-0 flex-1 space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-black text-slate-900 truncate">{c.title}</span>
                          {c.conversation_id === conversationId && (
                            <span className="text-[10px] font-black text-blue-700 bg-blue-100 px-2 py-0.5 rounded-md">
                              Active
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-slate-500 truncate font-medium">{c.last_message}</p>
                        <div className="flex items-center gap-3 text-[10px] text-slate-400 font-bold pt-1">
                          <span className="flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {c.updated_at ? new Date(c.updated_at).toLocaleDateString() : "Recent"}
                          </span>
                          <span>• {c.message_count} messages</span>
                          {c.products_discussed && c.products_discussed.length > 0 && (
                            <span className="truncate">• {c.products_discussed.join(", ")}</span>
                          )}
                        </div>
                      </div>
                      <button
                        onClick={(e) => handleDeleteConv(e, c.conversation_id)}
                        className="p-2 text-slate-400 hover:text-rose-600 rounded-xl hover:bg-rose-50 transition-colors shrink-0"
                        title="Delete conversation"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  ))
                )}
              </div>

              <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
                <button
                  onClick={() => {
                    handleNewChat();
                    setShowHistoryModal(false);
                  }}
                  className="flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl text-xs font-bold shadow-md shadow-blue-500/20 cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" /> Start New Conversation
                </button>
                <button
                  onClick={() => setShowHistoryModal(false)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-bold cursor-pointer"
                >
                  Close
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
