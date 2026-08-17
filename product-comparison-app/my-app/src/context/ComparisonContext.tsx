"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { Product } from "../app/types";
import {
  saveComparisonContext,
  getComparisonContext,
  clearComparisonContext,
  saveChatContext,
  getChatContext,
  clearChatContext,
  getOrCreateConversationId,
  clearAllContext,
  ComparisonContextData,
  ChatContextData,
} from "../services/storageService";
import {
  saveBackendSession,
  getBackendSession,
  deleteBackendSession,
  getUserConversationContext,
  saveUserConversationContext,
  getConversationMessages,
  deleteUserConversation,
  CompareResponseData,
  RecommendedItem,
  SourceCitation,
} from "../services/api";
import { getProductImage } from "../utils/imageHelper";

export interface ChatMessageItem {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date | string;
  products?: Product[];
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
  product?: Product | any;
}

interface ComparisonContextType {
  conversationId: string;
  selectedProducts: Product[];
  activeProduct: Product | null;
  comparisonResult: CompareResponseData | null;
  comparisonFields: string[];
  comparisonHistory: any[];
  messages: ChatMessageItem[];
  lastIntent: string;
  isRestoring: boolean;
  selectProduct: (product: Product) => void;
  removeProduct: (productId: string) => void;
  setSelectedProducts: React.Dispatch<React.SetStateAction<Product[]>>;
  clearSelectedProducts: () => void;
  setComparisonResult: (result: CompareResponseData | null) => void;
  setActiveProduct: (product: Product | null) => void;
  addMessage: (message: ChatMessageItem) => void;
  setMessages: React.Dispatch<React.SetStateAction<ChatMessageItem[]>>;
  clearAllSessionData: () => void;
  restoreSession: () => Promise<void>;
  loadConversation: (cid: string) => Promise<void>;
}

const ComparisonContext = createContext<ComparisonContextType | undefined>(undefined);

export function ComparisonProvider({ children }: { children: React.ReactNode }) {
  const [conversationId, setConversationIdState] = useState<string>("");
  const [selectedProducts, setSelectedProductsState] = useState<Product[]>([]);
  const [activeProduct, setActiveProductState] = useState<Product | null>(null);
  const [comparisonResult, setComparisonResultState] = useState<CompareResponseData | null>(null);
  const [comparisonFields, setComparisonFields] = useState<string[]>([
    "price", "cpu", "ram", "storage", "gpu", "display", "battery"
  ]);
  const [comparisonHistory, setComparisonHistory] = useState<any[]>([]);
  const [messages, setMessagesState] = useState<ChatMessageItem[]>([]);
  const [lastIntent, setLastIntent] = useState<string>("general");
  const [isRestoring, setIsRestoring] = useState<boolean>(true);

  // Initialize or restore conversation ID and session on load
  const hasRestoredRef = React.useRef(false);
  const restoreSession = useCallback(async () => {
    if (hasRestoredRef.current) return; // Prevent re-entry
    hasRestoredRef.current = true;
    setIsRestoring(true);
    try {
      const cid = getOrCreateConversationId();
      setConversationIdState(cid);

      // 1. First restore from local sessionStorage (instant UI response)
      const localComp = getComparisonContext();
      const localChat = getChatContext();

      let restoredProducts: Product[] = [];
      let restoredActiveProduct: Product | null = null;

      if (localComp && Array.isArray(localComp.products)) {
        const normalizedProds = localComp.products.map((p: any) => ({
          ...p,
          image: p.image_url || p.image || getProductImage(p),
          image_url: p.image_url || p.image || getProductImage(p),
        }));
        restoredProducts = normalizedProds;
        setSelectedProductsState(normalizedProds);
        if (localComp.comparisonResult) {
          setComparisonResultState(localComp.comparisonResult);
        }
        if (localComp.lastIntent) {
          setLastIntent(localComp.lastIntent);
        }
      }

      if (localChat && Array.isArray(localChat.messages) && localChat.messages.length > 0) {
        const parsedMsgs: ChatMessageItem[] = localChat.messages.map((m: any) => ({
          ...m,
          timestamp: m.timestamp ? new Date(m.timestamp) : new Date(),
        }));
        setMessagesState(parsedMsgs);
        if (localChat.active_product) {
          const act = localChat.active_product;
          restoredActiveProduct = {
            ...act,
            image: act.image_url || act.image || getProductImage(act),
            image_url: act.image_url || act.image || getProductImage(act),
          } as Product;
          setActiveProductState(restoredActiveProduct);
        }
      }

      // 2. Query MySQL Database Conversation Context & Messages for logged-in user
      const token = typeof window !== "undefined" ? localStorage.getItem("versus_ai_jwt") : null;
      if (token) {
        try {
          const dbContext = await getUserConversationContext(cid);
          if (dbContext && Array.isArray(dbContext.active_products) && dbContext.active_products.length > 0) {
            const dbProds = dbContext.active_products.map((p: any) => ({
              ...p,
              image: p.image_url || p.image || getProductImage(p),
              image_url: p.image_url || p.image || getProductImage(p),
            }));
            restoredProducts = dbProds;
            setSelectedProductsState(dbProds);
            setActiveProductState(dbProds[0] || null);
          }

          const dbMsgs = await getConversationMessages(cid);
          if (Array.isArray(dbMsgs) && dbMsgs.length > 0) {
            const formattedMsgs: ChatMessageItem[] = dbMsgs.map((m: any) => ({
              id: m.id || `msg_${Math.random()}`,
              role: m.role || "assistant",
              content: m.content || m.message || "",
              timestamp: m.timestamp ? new Date(m.timestamp) : new Date(),
              products: m.product_context || [],
            }));
            setMessagesState(formattedMsgs);
          }
        } catch (dbErr) {
          console.debug("Database context check:", dbErr);
        }
      }

      // 3. Query FastAPI Backend Session endpoint fallback
      try {
        const backendSession = await getBackendSession(cid);
        if (backendSession) {
          if (Array.isArray(backendSession.comparison_products) && backendSession.comparison_products.length > 0 && restoredProducts.length === 0) {
            const serverProds = backendSession.comparison_products.map((p: any) => ({
              ...p,
              image: p.image_url || p.image || getProductImage(p),
              image_url: p.image_url || p.image || getProductImage(p),
            }));
            setSelectedProductsState(serverProds);
          }
          if (backendSession.active_product && !restoredActiveProduct) {
            const act = backendSession.active_product;
            setActiveProductState({
              ...act,
              image: act.image_url || act.image || getProductImage(act),
              image_url: act.image_url || act.image || getProductImage(act),
            } as Product);
          }
        }
      } catch (backendErr) {
        console.debug("Backend session fallback check:", backendErr);
      }
    } catch (err) {
      console.warn("Session restore warning:", err);
    } finally {
      setIsRestoring(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Load a specific conversation from MySQL
  const loadConversation = useCallback(async (targetCid: string) => {
    if (!targetCid) return;
    setIsRestoring(true);
    try {
      setConversationIdState(targetCid);
      if (typeof window !== "undefined") {
        sessionStorage.setItem("versus_ai_conversation_id", targetCid);
      }

      // Fetch messages from MySQL
      const msgs = await getConversationMessages(targetCid);
      if (Array.isArray(msgs)) {
        const formatted: ChatMessageItem[] = msgs.map((m: any) => ({
          id: m.id || `msg_${Math.random()}`,
          role: m.role || "assistant",
          content: m.content || m.message || "",
          timestamp: m.timestamp ? new Date(m.timestamp) : new Date(),
          products: m.product_context || [],
        }));
        setMessagesState(formatted);
      }

      // Fetch context from MySQL
      const ctx = await getUserConversationContext(targetCid);
      if (ctx && Array.isArray(ctx.active_products) && ctx.active_products.length > 0) {
        const mapped = ctx.active_products.map((p: any) => ({
          ...p,
          image: p.image_url || p.image || getProductImage(p),
          image_url: p.image_url || p.image || getProductImage(p),
        }));
        setSelectedProductsState(mapped);
        setActiveProductState(mapped[0] || null);
      }
    } catch (err) {
      console.error("Failed to load conversation from MySQL:", err);
    } finally {
      setIsRestoring(false);
    }
  }, []);

  // Run on mount only
  useEffect(() => {
    restoreSession();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Sync state to sessionStorage and backend database
  const persistState = useCallback(
    (
      newSelected: Product[],
      newCompResult: CompareResponseData | null,
      newMsgs: ChatMessageItem[],
      newActiveProd: Product | null,
      newIntent: string
    ) => {
      const cid = conversationId || getOrCreateConversationId();

      // 1. Save comparison context to sessionStorage
      const compData: ComparisonContextData = {
        products: newSelected,
        selectedCount: newSelected.length,
        comparisonResult: newCompResult,
        comparisonFields,
        lastIntent: newIntent,
        timestamp: new Date().toISOString(),
      };
      saveComparisonContext(compData);

      // 2. Save chat context to sessionStorage
      const chatData: ChatContextData = {
        conversation_id: cid,
        messages: newMsgs,
        active_product: newActiveProd,
        comparison_products: newSelected,
        last_intent: newIntent,
        timestamp: new Date().toISOString(),
      };
      saveChatContext(chatData);

      // 3. Persist to MySQL Conversation Context if user is logged in
      const token = typeof window !== "undefined" ? localStorage.getItem("versus_ai_jwt") : null;
      if (token) {
        saveUserConversationContext(
          cid,
          newSelected,
          newSelected,
          newIntent
        ).catch((e) => console.debug("DB context auto-save warning:", e));
      }

      // 4. Auto-save to FastAPI Backend Session (non-blocking fallback)
      saveBackendSession({
        conversation_id: cid,
        comparison_products: newSelected.map((p) => p.id),
        selected_products: newSelected.map((p) => p.id),
        active_product: newActiveProd ? newActiveProd.id : undefined,
        messages: newMsgs.map((m) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          timestamp: m.timestamp instanceof Date ? m.timestamp.toISOString() : m.timestamp,
        })),
        last_intent: newIntent,
      }).catch((err) => {
        console.debug("Background session auto-save warning:", err);
      });
    },
    [conversationId, comparisonFields]
  );

  // Handlers
  const selectProduct = useCallback(
    (product: Product) => {
      setSelectedProductsState((prev) => {
        if (prev.some((p) => p.id === product.id)) return prev;
        const updated = [...prev, product];
        const newActive = updated[0] || null;
        setActiveProductState(newActive);
        persistState(updated, comparisonResult, messages, newActive, "selection");
        return updated;
      });
    },
    [comparisonResult, messages, persistState]
  );

  const removeProduct = useCallback(
    (productId: string) => {
      setSelectedProductsState((prev) => {
        const updated = prev.filter((p) => p.id !== productId);
        const newActive = updated[0] || null;
        setActiveProductState(newActive);
        persistState(updated, comparisonResult, messages, newActive, "removal");
        return updated;
      });
    },
    [comparisonResult, messages, persistState]
  );

  const setSelectedProducts = useCallback(
    (action: Product[] | ((prev: Product[]) => Product[])) => {
      setSelectedProductsState((prev) => {
        const updated = typeof action === "function" ? action(prev) : action;
        const newActive = updated[0] || null;
        setActiveProductState(newActive);
        persistState(updated, comparisonResult, messages, newActive, "selection");
        return updated;
      });
    },
    [comparisonResult, messages, persistState]
  );

  const clearSelectedProducts = useCallback(() => {
    setSelectedProductsState([]);
    setActiveProductState(null);
    setComparisonResultState(null);
    clearComparisonContext();
    persistState([], null, messages, null, "clear");
  }, [messages, persistState]);

  const setComparisonResult = useCallback(
    (result: CompareResponseData | null) => {
      setComparisonResultState(result);
      if (result) {
        setLastIntent("comparison");
      }
      persistState(selectedProducts, result, messages, activeProduct, "comparison");
    },
    [selectedProducts, messages, activeProduct, persistState]
  );

  const setActiveProduct = useCallback(
    (product: Product | null) => {
      setActiveProductState(product);
      persistState(selectedProducts, comparisonResult, messages, product, lastIntent);
    },
    [selectedProducts, comparisonResult, messages, lastIntent, persistState]
  );

  const addMessage = useCallback(
    (message: ChatMessageItem) => {
      setMessagesState((prev) => {
        const updated = [...prev, message];
        persistState(selectedProducts, comparisonResult, updated, activeProduct, lastIntent);
        return updated;
      });
    },
    [selectedProducts, comparisonResult, activeProduct, lastIntent, persistState]
  );

  const setMessages: React.Dispatch<React.SetStateAction<ChatMessageItem[]>> = useCallback(
    (action) => {
      setMessagesState((prev) => {
        const updated = typeof action === "function" ? action(prev) : action;
        persistState(selectedProducts, comparisonResult, updated, activeProduct, lastIntent);
        return updated;
      });
    },
    [selectedProducts, comparisonResult, activeProduct, lastIntent, persistState]
  );

  const clearAllSessionData = useCallback(() => {
    const cid = conversationId;
    setSelectedProductsState([]);
    setActiveProductState(null);
    setComparisonResultState(null);
    setMessagesState([]);
    setLastIntent("general");
    clearAllContext();
    if (cid) {
      deleteBackendSession(cid).catch(() => {});
      const token = typeof window !== "undefined" ? localStorage.getItem("versus_ai_jwt") : null;
      if (token) {
        deleteUserConversation(cid).catch(() => {});
      }
    }
  }, [conversationId]);

  return (
    <ComparisonContext.Provider
      value={{
        conversationId,
        selectedProducts,
        activeProduct,
        comparisonResult,
        comparisonFields,
        comparisonHistory,
        messages,
        lastIntent,
        isRestoring,
        selectProduct,
        removeProduct,
        setSelectedProducts,
        clearSelectedProducts,
        setComparisonResult,
        setActiveProduct,
        addMessage,
        setMessages,
        clearAllSessionData,
        restoreSession,
        loadConversation,
      }}
    >
      {children}
    </ComparisonContext.Provider>
  );
}

export function useComparison() {
  const context = useContext(ComparisonContext);
  if (!context) {
    throw new Error("useComparison must be used within a ComparisonProvider");
  }
  return context;
}
