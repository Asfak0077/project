/**
 * Client-Side Temporary Storage Service
 * Uses sessionStorage for temporary comparison and chat context persistence across page refreshes and browser reloads.
 * Automatically clears when the browser tab/session closes or when 24 hours have elapsed.
 */

const STORAGE_KEYS = {
  COMPARISON_CONTEXT: "versus_comparison_context",
  CHAT_CONTEXT: "versus_chat_context",
  CONVERSATION_ID: "versus_conversation_id",
  ACTIVE_PRODUCTS: "versus_active_products",
};

const TTL_MS = 24 * 60 * 60 * 1000; // 24 Hours in milliseconds

export interface StoredPayload<T> {
  data: T;
  createdAt: string;
  expiresAt: string;
}

export interface ComparisonContextData {
  products: any[];
  selectedCount: number;
  comparisonResult?: any;
  comparisonFields?: string[];
  lastIntent?: string;
  timestamp?: string;
}

export interface ChatContextData {
  conversation_id: string;
  messages: any[];
  active_product?: any;
  comparison_products?: any[];
  last_intent?: string;
  timestamp?: string;
}

function isStorageAvailable(): boolean {
  return typeof window !== "undefined";
}

function getItem(key: string): string | null {
  if (typeof window === "undefined") return null;
  try {
    const sVal = window.sessionStorage?.getItem(key);
    if (sVal) return sVal;
  } catch {}
  try {
    const lVal = window.localStorage?.getItem(key);
    if (lVal) return lVal;
  } catch {}
  return null;
}

function setItem(key: string, value: string): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage?.setItem(key, value);
  } catch {}
  try {
    window.localStorage?.setItem(key, value);
  } catch {}
}

function removeItem(key: string): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage?.removeItem(key);
  } catch {}
  try {
    window.localStorage?.removeItem(key);
  } catch {}
}

function wrapPayload<T>(data: T): StoredPayload<T> {
  const now = new Date();
  const expiresAt = new Date(now.getTime() + TTL_MS);
  return {
    data,
    createdAt: now.toISOString(),
    expiresAt: expiresAt.toISOString(),
  };
}

function unwrapPayload<T>(rawString: string | null, clearFn: () => void): T | null {
  if (!rawString) return null;
  try {
    const payload = JSON.parse(rawString) as StoredPayload<T>;
    if (!payload || !payload.expiresAt) return null;

    const expiry = new Date(payload.expiresAt).getTime();
    if (Date.now() > expiry) {
      clearFn();
      return null;
    }
    return payload.data;
  } catch (err) {
    console.warn("Error parsing storage item:", err);
    clearFn();
    return null;
  }
}

// ============================================================================
// CONVERSATION ID
// ============================================================================

export function getOrCreateConversationId(): string {
  if (!isStorageAvailable()) {
    return "conv_" + Date.now() + "_" + Math.random().toString(36).substring(2, 9);
  }
  let cid = getItem(STORAGE_KEYS.CONVERSATION_ID);
  if (!cid) {
    cid = "conv_" + Date.now() + "_" + Math.random().toString(36).substring(2, 9);
    setItem(STORAGE_KEYS.CONVERSATION_ID, cid);
  }
  return cid;
}

export function setConversationId(id: string): void {
  if (isStorageAvailable() && id) {
    setItem(STORAGE_KEYS.CONVERSATION_ID, id);
  }
}

// ============================================================================
// COMPARISON CONTEXT
// ============================================================================

export function saveComparisonContext(context: ComparisonContextData): void {
  if (!isStorageAvailable()) return;
  try {
    const payload = wrapPayload(context);
    setItem(STORAGE_KEYS.COMPARISON_CONTEXT, JSON.stringify(payload));
  } catch (err) {
    console.warn("Failed to save comparison context to storage:", err);
  }
}

export function getComparisonContext(): ComparisonContextData | null {
  if (!isStorageAvailable()) return null;
  const raw = getItem(STORAGE_KEYS.COMPARISON_CONTEXT);
  return unwrapPayload<ComparisonContextData>(raw, clearComparisonContext);
}

export function clearComparisonContext(): void {
  if (isStorageAvailable()) {
    removeItem(STORAGE_KEYS.COMPARISON_CONTEXT);
  }
}

// ============================================================================
// CHAT CONTEXT
// ============================================================================

export function saveChatContext(context: ChatContextData): void {
  if (!isStorageAvailable()) return;
  try {
    const payload = wrapPayload(context);
    setItem(STORAGE_KEYS.CHAT_CONTEXT, JSON.stringify(payload));
  } catch (err) {
    console.warn("Failed to save chat context to storage:", err);
  }
}

export function getChatContext(): ChatContextData | null {
  if (!isStorageAvailable()) return null;
  const raw = getItem(STORAGE_KEYS.CHAT_CONTEXT);
  return unwrapPayload<ChatContextData>(raw, clearChatContext);
}

export function clearChatContext(): void {
  if (isStorageAvailable()) {
    removeItem(STORAGE_KEYS.CHAT_CONTEXT);
  }
}

// ============================================================================
// ALL CONTEXT
// ============================================================================

export function clearAllContext(): void {
  clearComparisonContext();
  clearChatContext();
  if (isStorageAvailable()) {
    removeItem(STORAGE_KEYS.CONVERSATION_ID);
    removeItem(STORAGE_KEYS.ACTIVE_PRODUCTS);
  }
}

const storageService = {
  saveComparisonContext,
  getComparisonContext,
  clearComparisonContext,
  saveChatContext,
  getChatContext,
  clearChatContext,
  clearAllContext,
  getOrCreateConversationId,
  setConversationId,
};

export default storageService;
