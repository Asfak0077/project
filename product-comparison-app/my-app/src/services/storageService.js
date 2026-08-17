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

function isStorageAvailable() {
  return typeof window !== "undefined" && typeof window.sessionStorage !== "undefined";
}

function wrapPayload(data) {
  const now = new Date();
  const expiresAt = new Date(now.getTime() + TTL_MS);
  return {
    data,
    createdAt: now.toISOString(),
    expiresAt: expiresAt.toISOString(),
  };
}

function unwrapPayload(rawString, clearFn) {
  if (!rawString) return null;
  try {
    const payload = JSON.parse(rawString);
    if (!payload || !payload.expiresAt) return null;

    const expiry = new Date(payload.expiresAt).getTime();
    if (Date.now() > expiry) {
      clearFn();
      return null;
    }
    return payload.data;
  } catch (err) {
    console.warn("Error parsing sessionStorage item:", err);
    clearFn();
    return null;
  }
}

// ============================================================================
// CONVERSATION ID
// ============================================================================

export function getOrCreateConversationId() {
  if (!isStorageAvailable()) {
    return "conv_" + Date.now() + "_" + Math.random().toString(36).substring(2, 9);
  }
  let cid = sessionStorage.getItem(STORAGE_KEYS.CONVERSATION_ID);
  if (!cid) {
    cid = "conv_" + Date.now() + "_" + Math.random().toString(36).substring(2, 9);
    sessionStorage.setItem(STORAGE_KEYS.CONVERSATION_ID, cid);
  }
  return cid;
}

export function setConversationId(id) {
  if (isStorageAvailable() && id) {
    sessionStorage.setItem(STORAGE_KEYS.CONVERSATION_ID, id);
  }
}

// ============================================================================
// COMPARISON CONTEXT
// ============================================================================

export function saveComparisonContext(context) {
  if (!isStorageAvailable()) return;
  try {
    const payload = wrapPayload(context);
    sessionStorage.setItem(STORAGE_KEYS.COMPARISON_CONTEXT, JSON.stringify(payload));
  } catch (err) {
    console.warn("Failed to save comparison context to sessionStorage:", err);
  }
}

export function getComparisonContext() {
  if (!isStorageAvailable()) return null;
  const raw = sessionStorage.getItem(STORAGE_KEYS.COMPARISON_CONTEXT);
  return unwrapPayload(raw, clearComparisonContext);
}

export function clearComparisonContext() {
  if (isStorageAvailable()) {
    sessionStorage.removeItem(STORAGE_KEYS.COMPARISON_CONTEXT);
  }
}

// ============================================================================
// CHAT CONTEXT
// ============================================================================

export function saveChatContext(context) {
  if (!isStorageAvailable()) return;
  try {
    const payload = wrapPayload(context);
    sessionStorage.setItem(STORAGE_KEYS.CHAT_CONTEXT, JSON.stringify(payload));
  } catch (err) {
    console.warn("Failed to save chat context to sessionStorage:", err);
  }
}

export function getChatContext() {
  if (!isStorageAvailable()) return null;
  const raw = sessionStorage.getItem(STORAGE_KEYS.CHAT_CONTEXT);
  return unwrapPayload(raw, clearChatContext);
}

export function clearChatContext() {
  if (isStorageAvailable()) {
    sessionStorage.removeItem(STORAGE_KEYS.CHAT_CONTEXT);
  }
}

// ============================================================================
// ALL CONTEXT
// ============================================================================

export function clearAllContext() {
  clearComparisonContext();
  clearChatContext();
  if (isStorageAvailable()) {
    sessionStorage.removeItem(STORAGE_KEYS.CONVERSATION_ID);
    sessionStorage.removeItem(STORAGE_KEYS.ACTIVE_PRODUCTS);
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
