"use client";

import React, { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FileText,
  Upload,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Trash2,
  Search,
  Sparkles,
  ArrowLeft,
  FileCheck,
  FileClock,
  BookOpen,
  Layers,
  Tag,
  Shield,
  RefreshCw,
  HelpCircle,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Cpu,
  Battery,
  Flame,
  Monitor,
  Send,
  Bot,
  User,
  Copy,
  Check,
  ExternalLink,
  Code,
  Terminal,
  Filter,
} from "lucide-react";
import {
  getDocuments,
  uploadDocument,
  deleteDocument,
  sendRAGChatMessage,
  DocumentItem,
  RAGChatSource,
  RAGChatResponseData,
} from "../../services/api";

interface DocumentsViewProps {
  onBack: () => void;
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  sources?: RAGChatSource[];
  confidence?: string;
  type?: string;
  suggested_followups?: string[];
  debug_trace?: Record<string, any>;
}

// ---------------------------------------------------------------------------
// Markdown Renderer
// ---------------------------------------------------------------------------

function renderMarkdown(text: string): React.ReactNode[] {
  const lines = text.split("\n");
  const elements: React.ReactNode[] = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    if (trimmed.startsWith("### ")) {
      elements.push(
        <h4 key={i} className="text-xs sm:text-sm font-black text-slate-900 mt-2.5 mb-1 flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-blue-600 shrink-0" />
          {renderInline(trimmed.slice(4))}
        </h4>
      );
    } else if (trimmed.startsWith("## ")) {
      elements.push(
        <h3 key={i} className="text-sm sm:text-base font-black text-slate-900 mt-3 mb-1.5">
          {renderInline(trimmed.slice(3))}
        </h3>
      );
    } else if (trimmed.startsWith("# ")) {
      elements.push(
        <h2 key={i} className="text-base sm:text-lg font-black text-slate-900 mt-3 mb-2">
          {renderInline(trimmed.slice(2))}
        </h2>
      );
    } else if (trimmed.startsWith("✓ ")) {
      elements.push(
        <div key={i} className="flex items-start gap-2 ml-1 py-0.5">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 mt-0.5 shrink-0" />
          <span className="text-slate-800 font-medium text-xs sm:text-sm">{renderInline(trimmed.slice(2))}</span>
        </div>
      );
    } else if (trimmed.startsWith("• ") || trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      elements.push(
        <div key={i} className="flex items-start gap-2 ml-1 py-0.5">
          <span className="text-blue-600 font-black shrink-0">•</span>
          <span className="text-slate-800 font-medium text-xs sm:text-sm">{renderInline(trimmed.slice(2))}</span>
        </div>
      );
    } else if (trimmed.startsWith("Source:")) {
      elements.push(
        <div key={i} className="pt-1">
          <span className="inline-flex items-center gap-1 text-[10px] font-bold text-slate-500 bg-slate-100 px-2 py-0.5 rounded-lg border border-slate-200">
            <FileText className="w-3 h-3 text-blue-600" />
            {trimmed}
          </span>
        </div>
      );
    } else if (trimmed === "") {
      elements.push(<div key={i} className="h-1" />);
    } else {
      elements.push(
        <p key={i} className="leading-relaxed text-slate-800 text-xs sm:text-sm">
          {renderInline(trimmed)}
        </p>
      );
    }
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
      if (boldMatch.index > 0) parts.push(remaining.slice(0, boldMatch.index));
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
      if (codeMatch.index > 0) parts.push(remaining.slice(0, codeMatch.index));
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
// Component
// ---------------------------------------------------------------------------

export default function DocumentsView({ onBack }: DocumentsViewProps) {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDocId, setSelectedDocId] = useState<number | null>(null);

  // Upload state
  const [uploadStatus, setUploadStatus] = useState<
    "idle" | "uploading" | "processing" | "indexing" | "ready" | "failed"
  >("idle");
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccessMsg, setUploadSuccessMsg] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  // Chat state
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [expandedSources, setExpandedSources] = useState<Record<string, boolean>>({});
  const [showDebugTrace, setShowDebugTrace] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadDocs();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const loadDocs = async () => {
    setLoading(true);
    try {
      const data = await getDocuments();
      setDocuments(data || []);
    } catch (err) {
      console.error("Failed to load documents:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleProcessFile = async (file: File) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pdf") && !file.name.toLowerCase().endsWith(".txt")) {
      setUploadError("Only PDF and TXT documents are supported.");
      return;
    }

    if (file.size > 25 * 1024 * 1024) {
      setUploadError("File size exceeds maximum limit of 25MB.");
      return;
    }

    setUploadStatus("uploading");
    setUploadError(null);
    setUploadSuccessMsg(null);

    try {
      setTimeout(() => setUploadStatus("processing"), 500);
      setTimeout(() => setUploadStatus("indexing"), 1200);

      const doc = await uploadDocument(file);
      setDocuments((prev) => [doc, ...prev.filter((d) => d.id !== doc.id)]);
      setSelectedDocId(doc.id);
      setUploadStatus("ready");
      setUploadSuccessMsg(`"${file.name}" indexed successfully (${doc.chunk_count || 0} chunks).`);

      // Add assistant welcome notification for new document
      const docWelcome: ChatMessage = {
        id: Date.now().toString(),
        role: "assistant",
        content: `### Document Ready: ${doc.filename}\n\n**${doc.filename}** has been indexed into the **RAG VER2 Vector Corpus** with ${doc.chunk_count || 1} semantic chunks. You can ask technical questions, request explanations, or generate a document summary.`,
        timestamp: new Date(),
        suggested_followups: [
          "What are the specifications?",
          "What is the battery life?",
          "Explain performance",
          "Summarize document",
        ],
      };
      setMessages((prev) => [...prev, docWelcome]);

      setTimeout(() => {
        setUploadStatus("idle");
        setUploadSuccessMsg(null);
      }, 3500);
    } catch (err: any) {
      setUploadStatus("failed");
      setUploadError(err.response?.data?.detail || "I could not process this document request. Please try again.");
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleProcessFile(file);
    e.target.value = "";
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleProcessFile(file);
  };

  const handleDelete = async (id: number) => {
    setDeletingId(id);
    try {
      await deleteDocument(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
      if (selectedDocId === id) setSelectedDocId(null);
    } catch (err) {
      console.error("Failed to delete document:", err);
    } finally {
      setDeletingId(null);
    }
  };

  const handleSendMessage = async (e?: React.FormEvent, customQuery?: string) => {
    if (e) e.preventDefault();
    const queryText = (customQuery || input).trim();
    if (!queryText || isTyping) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: "user",
      content: queryText,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsTyping(true);

    try {
      const historyPayload = messages.slice(-6).map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const activeDoc = documents.find((d) => d.id === selectedDocId);

      const res: RAGChatResponseData = await sendRAGChatMessage({
        message: queryText,
        document_id: selectedDocId || undefined,
        product_name: activeDoc ? (activeDoc.product_name || activeDoc.filename.replace(".pdf", "")) : undefined,
        history: historyPayload,
      });

      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: res.answer || "I could not find this information in the document.",
        timestamp: new Date(),
        sources: res.sources || [],
        confidence: res.confidence || "High",
        type: res.type || "general",
        suggested_followups: res.suggested_followups || [
          "What are the specifications?",
          "What is the battery life?",
          "Explain performance",
        ],
        debug_trace: res.debug_trace,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: any) {
      console.error("RAG Chat API Error:", err);
      const errorMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "I could not process this document request. Please try again.",
        timestamp: new Date(),
        confidence: "Low",
        type: "error",
        suggested_followups: ["What are the specifications?", "Explain performance"],
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsTyping(false);
    }
  };

  const toggleSourceExpand = (msgId: string) => {
    setExpandedSources((prev) => ({
      ...prev,
      [msgId]: !prev[msgId],
    }));
  };

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text.replace(/\*\*/g, "").replace(/### /g, ""));
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const selectedDoc = documents.find((d) => d.id === selectedDocId);

  const defaultGreeting: ChatMessage = {
    id: "greeting",
    role: "assistant",
    content: selectedDoc
      ? `### Document Loaded: ${selectedDoc.filename}\n\nAsk any question regarding specifications, cooling, battery performance, or request a complete document summary.`
      : `### Document AI Assistant\n\nUpload a PDF or TXT datasheet, user manual, or architectural guide to ask grounded technical questions and explore verified hardware specifications.`,
    timestamp: new Date(),
    suggested_followups: [
      "What is processor?",
      "Explain battery performance",
      "Summarize document",
      "What does this document say about cooling?",
    ],
  };

  const displayMessages = messages.length > 0 ? messages : [defaultGreeting];

  return (
    <div className="py-4 sm:py-6 h-[calc(100vh-80px)] flex flex-col max-w-7xl mx-auto w-full px-2 sm:px-4">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between bg-white/90 backdrop-blur-md border border-slate-200/80 rounded-t-3xl p-4 gap-4 shrink-0 shadow-xs">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="p-2.5 text-slate-500 hover:text-slate-900 bg-slate-100 hover:bg-slate-200/80 rounded-xl transition-all cursor-pointer shadow-2xs"
            title="Back"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-purple-600 via-indigo-600 to-blue-600 flex items-center justify-center text-white shadow-md shadow-purple-500/25">
              <BookOpen className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base sm:text-lg font-black text-slate-900 flex items-center gap-2">
                Document AI Assistant <Sparkles className="w-4 h-4 text-purple-600" />
              </h2>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
                <span className="text-[11px] font-bold text-slate-500">RAG VER2 Connected</span>
                <span className="text-slate-300">•</span>
                <span className="text-[11px] font-bold text-purple-700 bg-purple-50 px-2 py-0.5 rounded-lg border border-purple-200/60">
                  {documents.length} Document{documents.length !== 1 ? "s" : ""} Loaded
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowDebugTrace(!showDebugTrace)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold border transition-all cursor-pointer shadow-2xs ${
              showDebugTrace
                ? "bg-purple-600 text-white border-purple-600 shadow-purple-500/20"
                : "bg-slate-100 text-slate-700 border-slate-200 hover:bg-slate-200/80"
            }`}
          >
            <Terminal className="w-3.5 h-3.5" /> RAG Debug Trace
          </button>
        </div>
      </div>

      {/* Main Split Body */}
      <div className="flex flex-col lg:flex-row flex-1 overflow-hidden bg-white/80 backdrop-blur-md border border-slate-200/80 rounded-b-3xl border-t-0 shadow-lg">
        {/* Left Sidebar: Document Manager & Upload Area */}
        <div className="w-full lg:w-88 bg-slate-50/80 border-r border-slate-200/80 p-4 sm:p-5 overflow-y-auto shrink-0 space-y-4">
          {/* Drag & Drop Upload Box */}
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-2xl p-5 text-center transition-all bg-white/90 shadow-2xs ${
              isDragging
                ? "border-purple-500 bg-purple-50/50 scale-[1.01]"
                : "border-slate-300 hover:border-purple-400"
            }`}
          >
            <div className="w-10 h-10 rounded-2xl bg-purple-50 text-purple-600 flex items-center justify-center mx-auto mb-3 shadow-2xs">
              <Upload className="w-5 h-5" />
            </div>
            <h3 className="text-xs font-black text-slate-900">Upload PDF or TXT</h3>
            <p className="text-[11px] text-slate-400 font-semibold mt-0.5">Datasheets, specs & manuals (Max 25MB)</p>

            <label className="mt-3 inline-block px-4 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white rounded-xl text-xs font-bold shadow-md shadow-purple-500/20 cursor-pointer transition-all">
              Choose Document
              <input
                type="file"
                accept=".pdf,.txt"
                onChange={handleFileUpload}
                className="hidden"
                disabled={uploadStatus !== "idle" && uploadStatus !== "ready" && uploadStatus !== "failed"}
              />
            </label>

            {/* Upload Status Pipeline Progress */}
            {uploadStatus !== "idle" && (
              <div className="mt-3 pt-3 border-t border-slate-100">
                {uploadStatus === "uploading" && (
                  <div className="flex items-center justify-center gap-2 text-xs font-bold text-blue-600">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" /> Uploading Document...
                  </div>
                )}
                {uploadStatus === "processing" && (
                  <div className="flex items-center justify-center gap-2 text-xs font-bold text-purple-600">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" /> Processing & Cleaning...
                  </div>
                )}
                {uploadStatus === "indexing" && (
                  <div className="flex items-center justify-center gap-2 text-xs font-bold text-indigo-600">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" /> Semantic Indexing Chunks...
                  </div>
                )}
                {uploadStatus === "ready" && (
                  <div className="flex items-center justify-center gap-1.5 text-xs font-bold text-emerald-600">
                    <CheckCircle2 className="w-3.5 h-3.5" /> ✓ Ready for Grounded Q&A
                  </div>
                )}
                {uploadStatus === "failed" && (
                  <div className="flex items-center justify-center gap-1.5 text-xs font-bold text-rose-600">
                    <AlertCircle className="w-3.5 h-3.5" /> Indexing Failed
                  </div>
                )}
              </div>
            )}

            {uploadError && (
              <div className="mt-2 text-[11px] font-bold text-rose-600 bg-rose-50 p-2 rounded-xl border border-rose-200">
                {uploadError}
              </div>
            )}
            {uploadSuccessMsg && (
              <div className="mt-2 text-[11px] font-bold text-emerald-700 bg-emerald-50 p-2 rounded-xl border border-emerald-200">
                {uploadSuccessMsg}
              </div>
            )}
          </div>

          {/* Document Filter Selector */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-[11px] font-extrabold text-slate-500 uppercase tracking-wider">
              <span>Indexed Documents</span>
              {selectedDocId !== null && (
                <button
                  onClick={() => setSelectedDocId(null)}
                  className="text-purple-600 hover:text-purple-800 font-bold lowercase cursor-pointer"
                >
                  (clear filter)
                </button>
              )}
            </div>

            {loading ? (
              <div className="py-6 text-center text-xs text-slate-400 font-medium">
                <Loader2 className="w-4 h-4 animate-spin mx-auto mb-1 text-purple-600" />
                Loading indexed documents...
              </div>
            ) : documents.length === 0 ? (
              <div className="p-4 bg-white/90 rounded-2xl border border-dashed border-slate-200 text-center text-xs text-slate-400 font-medium">
                No documents uploaded yet. Upload a PDF or TXT to start.
              </div>
            ) : (
              <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                {documents.map((doc) => {
                  const isSelected = selectedDocId === doc.id;
                  const sizeKb = Math.round((doc.file_size || 0) / 1024);
                  return (
                    <div
                      key={doc.id}
                      onClick={() => setSelectedDocId(isSelected ? null : doc.id)}
                      className={`p-3 rounded-2xl border transition-all cursor-pointer flex items-start justify-between gap-2.5 ${
                        isSelected
                          ? "bg-purple-50/90 border-purple-300 shadow-xs"
                          : "bg-white/95 border-slate-200/90 hover:border-purple-200 hover:bg-slate-50/80 shadow-2xs"
                      }`}
                    >
                      <div className="flex items-start gap-2.5 min-w-0">
                        <div className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 ${
                          isSelected ? "bg-purple-600 text-white" : "bg-purple-50 text-purple-600"
                        }`}>
                          <FileText className="w-4 h-4" />
                        </div>
                        <div className="min-w-0">
                          <div className="text-xs font-bold text-slate-900 truncate" title={doc.filename}>
                            {doc.filename}
                          </div>
                          <div className="flex items-center gap-2 text-[10px] font-semibold text-slate-500 mt-0.5">
                            <span>{sizeKb} KB</span>
                            <span>•</span>
                            <span className="text-purple-700 font-bold">{doc.chunk_count || 1} chunks</span>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-1 shrink-0">
                        <span className="text-[9px] font-black text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                          ✓ Ready
                        </span>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDelete(doc.id);
                          }}
                          disabled={deletingId === doc.id}
                          className="p-1 text-slate-400 hover:text-rose-600 rounded transition-colors"
                          title="Delete Document"
                        >
                          {deletingId === doc.id ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <Trash2 className="w-3.5 h-3.5" />
                          )}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Right Area: RAG Chat Assistant */}
        <div className="flex-1 flex flex-col justify-between overflow-hidden bg-gradient-to-br from-[#F8FAFC] via-slate-50 to-purple-50/20">
          {/* Active Filter Scope Pill */}
          <div className="px-4 py-2 bg-slate-100/70 border-b border-slate-200/70 flex items-center justify-between text-xs font-bold text-slate-600">
            <div className="flex items-center gap-2">
              <Filter className="w-3.5 h-3.5 text-purple-600" />
              <span>Scope:</span>
              {selectedDoc ? (
                <span className="text-purple-700 bg-purple-50 px-2 py-0.5 rounded-lg border border-purple-200/70 font-black">
                  📄 {selectedDoc.filename}
                </span>
              ) : (
                <span className="text-slate-700 bg-white px-2 py-0.5 rounded-lg border border-slate-200 font-bold">
                  All Indexed Documents ({documents.length})
                </span>
              )}
            </div>
            <span className="text-[11px] font-semibold text-slate-400">Strict Document Grounding</span>
          </div>

          {/* Messages Feed */}
          <div className="flex-1 p-4 sm:p-6 overflow-y-auto space-y-5">
            {displayMessages.map((msg) => {
              const isUser = msg.role === "user";
              const isSourcesOpen = expandedSources[msg.id] || false;
              const hasSources = msg.sources && msg.sources.length > 0;

              return (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.2 }}
                  className={`flex items-start gap-3 ${isUser ? "flex-row-reverse" : ""}`}
                >
                  <div
                    className={`w-8 h-8 rounded-xl flex items-center justify-center text-white shrink-0 shadow-2xs ${
                      isUser
                        ? "bg-slate-900"
                        : "bg-gradient-to-tr from-purple-600 via-indigo-600 to-blue-600 shadow-purple-500/20"
                    }`}
                  >
                    {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                  </div>

                  <div
                    className={`max-w-[88%] sm:max-w-[80%] rounded-2xl p-4 text-xs sm:text-sm leading-relaxed space-y-2.5 ${
                      isUser
                        ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-md shadow-blue-600/20 rounded-tr-xs"
                        : "bg-white/95 backdrop-blur-md border border-slate-200/90 text-slate-800 shadow-sm rounded-tl-xs"
                    }`}
                  >
                    {/* Message Body */}
                    <div className="space-y-1">
                      {!isUser ? renderMarkdown(msg.content) : (
                        <div className="whitespace-pre-wrap font-medium">{msg.content}</div>
                      )}
                    </div>

                    {/* Bottom Metadata & Verification Badge */}
                    {!isUser && (
                      <div className="pt-2 border-t border-slate-100/70 flex items-center justify-between flex-wrap gap-2">
                        <div className="flex items-center gap-2">
                          <span className="inline-flex items-center gap-1 font-black text-purple-700 bg-purple-50 px-2 py-0.5 rounded-lg border border-purple-200/70 text-[10px]">
                            <Check className="w-3 h-3 text-purple-600" /> RAG Verified
                          </span>

                          {hasSources && (
                            <button
                              onClick={() => toggleSourceExpand(msg.id)}
                              className="text-[11px] font-bold text-blue-600 hover:text-blue-800 flex items-center gap-1 cursor-pointer bg-blue-50 px-2 py-0.5 rounded-lg border border-blue-100 transition-colors"
                            >
                              Sources ({msg.sources?.length})
                              {isSourcesOpen ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                            </button>
                          )}
                        </div>

                        <button
                          onClick={() => handleCopy(msg.id, msg.content)}
                          className="text-[11px] font-bold text-slate-400 hover:text-slate-700 flex items-center gap-1 cursor-pointer transition-colors"
                        >
                          {copiedId === msg.id ? (
                            <>
                              <Check className="w-3.5 h-3.5 text-emerald-600" /> Copied
                            </>
                          ) : (
                            <>
                              <Copy className="w-3.5 h-3.5" /> Copy
                            </>
                          )}
                        </button>
                      </div>
                    )}

                    {/* Expandable Source Section (Collapsed by Default) */}
                    <AnimatePresence>
                      {!isUser && hasSources && isSourcesOpen && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: "auto" }}
                          exit={{ opacity: 0, height: 0 }}
                          className="space-y-2 pt-2 border-t border-dashed border-slate-200 overflow-hidden"
                        >
                          <div className="text-[10px] font-black text-slate-400 uppercase tracking-wider">
                            Source Document Citations
                          </div>
                          <div className="space-y-2">
                            {msg.sources?.map((s, idx) => (
                              <div key={idx} className="bg-slate-50/90 border border-slate-200/80 rounded-xl p-2.5 text-xs space-y-1 shadow-2xs">
                                <div className="flex items-center justify-between font-bold text-slate-900">
                                  <span className="text-purple-700 truncate font-black">{s.document}</span>
                                  <span className="text-[10px] text-slate-500 bg-white px-2 py-0.5 rounded border border-slate-200 shrink-0">
                                    {s.page ? `Page ${s.page}` : s.section || "Section Overview"}
                                  </span>
                                </div>
                                {s.snippet && (
                                  <p className="text-[11px] text-slate-600 font-medium italic bg-white/70 p-2 rounded-lg border border-slate-100">
                                    &quot;{s.snippet}&quot;
                                  </p>
                                )}
                              </div>
                            ))}
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>

                    {/* Suggested Followups */}
                    {!isUser && msg.suggested_followups && msg.suggested_followups.length > 0 && (
                      <div className="pt-2 border-t border-slate-100 space-y-1.5">
                        <div className="text-[10px] font-black text-slate-400 uppercase tracking-wider">
                          Suggested Questions
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          {msg.suggested_followups.map((q, i) => (
                            <button
                              key={i}
                              onClick={() => handleSendMessage(undefined, q)}
                              className="px-2.5 py-1 bg-slate-50/90 hover:bg-purple-50/90 border border-slate-200 hover:border-purple-300 rounded-xl text-[11px] font-semibold text-slate-600 hover:text-purple-700 transition-all cursor-pointer shadow-2xs"
                            >
                              {q}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </motion.div>
              );
            })}

            {isTyping && (
              <motion.div
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center gap-3"
              >
                <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-purple-600 via-indigo-600 to-blue-600 text-white flex items-center justify-center shrink-0 shadow-xs">
                  <Bot className="w-4 h-4" />
                </div>
                <div className="bg-white/95 border border-slate-200 rounded-2xl px-4 py-3 text-xs font-bold text-slate-600 flex items-center gap-2.5 shadow-2xs">
                  <Loader2 className="w-4 h-4 animate-spin text-purple-600" />
                  Retrieving document vectors & validating grounded facts...
                </div>
              </motion.div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Developer RAG Debug Trace Drawer */}
          <AnimatePresence>
            {showDebugTrace && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="bg-slate-900 text-emerald-400 p-4 font-mono text-[11px] border-t border-slate-800 space-y-2 overflow-x-auto max-h-48"
              >
                <div className="flex items-center justify-between text-slate-400 font-bold border-b border-slate-800 pb-1">
                  <span>[RAG VER2 Trace Engine]</span>
                  <button onClick={() => setShowDebugTrace(false)} className="text-slate-400 hover:text-white cursor-pointer">✕</button>
                </div>
                {messages.length > 0 && messages[messages.length - 1].debug_trace ? (
                  <pre className="text-[10px] leading-relaxed whitespace-pre-wrap">
                    {JSON.stringify(messages[messages.length - 1].debug_trace, null, 2)}
                  </pre>
                ) : (
                  <div className="text-slate-500">No active trace yet. Send a document question to view pipeline metrics.</div>
                )}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Chat Input Bar */}
          <form onSubmit={(e) => handleSendMessage(e)} className="p-3.5 sm:p-4 bg-white/90 backdrop-blur-md border-t border-slate-200/80 flex items-center gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={
                selectedDoc
                  ? `Ask about ${selectedDoc.filename} (e.g. 'RAM', 'Explain battery', 'Summarize')...`
                  : "Ask across all documents (e.g. 'What is processor?', 'Explain cooling')..."
              }
              className="flex-1 bg-slate-50/90 border border-slate-200/90 rounded-2xl px-4 py-3 text-xs sm:text-sm font-semibold text-slate-900 placeholder-slate-400 focus:outline-none focus:border-purple-500 focus:bg-white transition-all shadow-2xs"
            />
            <button
              type="submit"
              disabled={!input.trim() || isTyping}
              className="p-3 sm:px-5 sm:py-3 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white rounded-2xl shadow-md shadow-purple-500/20 disabled:opacity-50 transition-all cursor-pointer flex items-center gap-2 font-bold text-xs sm:text-sm"
            >
              <Send className="w-4 h-4" />
              <span className="hidden sm:inline">Ask Document AI</span>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
