import axios, { AxiosInstance } from "axios";
import {
  Product,
  UserProfile,
  UserPreferences,
  AppNotification,
  NotificationListResponse,
  BattleResultData,
  BattleHistoryResponse,
} from "../app/types";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
export const BACKEND_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api").replace(/\/api\/?$/, "");

export const getAssetUrl = (url?: string): string => {
  if (!url) return "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200&auto=format&fit=crop&q=80";
  if (url.startsWith("http://") || url.startsWith("https://") || url.startsWith("data:")) return url;
  return `${BACKEND_URL}${url.startsWith("/") ? "" : "/"}${url}`;
};

const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Attach JWT Bearer token to all outgoing requests
api.interceptors.request.use(
  (config) => {
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("versus_ai_jwt");
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor with user-friendly error formatting
api.interceptors.response.use(
  (response) => response,
  (error) => {
    let message = "An unexpected error occurred.";
    if (error.response) {
      const status = error.response.status;
      const data = error.response.data;

      if (status === 401) {
        message = "Authentication token required or expired. Please log in.";
      } else if (status === 403) {
        message = data?.detail || "You do not have permission to perform this action.";
      } else if (status === 404) {
        message = data?.detail || "Requested resource could not be found.";
      } else if (status === 422) {
        message = data?.detail ? (typeof data.detail === "string" ? data.detail : "Unable to process request. Please check your inputs.") : "Unable to process request. Please try again.";
      } else if (data?.detail) {
        message = typeof data.detail === "string" ? data.detail : "Unable to process request. Please try again.";
      }
    } else if (error.request) {
      message = "Unable to reach server. Please check your network connection.";
    }
    return Promise.reject(new Error(message));
  }
);

// ============================================================
// AUTHENTICATION APIs
// ============================================================

export interface AuthResponseData {
  token: string;
  user_id: number;
  name: string;
  email: string;
  role: string;
  avatar?: string;
}

export const registerUser = async (name: string, email: string, password: string, confirmPassword?: string): Promise<AuthResponseData> => {
  const res = await api.post("/auth/register", { name, email, password, confirm_password: confirmPassword });
  if (res.data?.token && typeof window !== "undefined") {
    localStorage.setItem("versus_ai_jwt", res.data.token);
  }
  return res.data;
};

export const loginUser = async (email: string, password: string): Promise<AuthResponseData> => {
  const res = await api.post("/auth/login", { email, password });
  if (res.data?.token && typeof window !== "undefined") {
    localStorage.setItem("versus_ai_jwt", res.data.token);
  }
  return res.data;
};

export const googleAuthLogin = async (credential: string): Promise<AuthResponseData> => {
  const res = await api.post("/auth/google", { credential });
  if (res.data?.token && typeof window !== "undefined") {
    localStorage.setItem("versus_ai_jwt", res.data.token);
  }
  return res.data;
};

export const requestPasswordReset = async (email: string) => {
  const res = await api.post("/auth/forgot-password", { email });
  return res.data;
};

export const verifyPasswordOTP = async (email: string, otp_code: string, new_password: string) => {
  const res = await api.post("/auth/verify-otp", { email, otp_code, new_password });
  return res.data;
};

// ============================================================
// USER PROFILE & PREFERENCES APIs
// ============================================================

export const getProfile = async (): Promise<UserProfile> => {
  const res = await api.get("/users/profile");
  return res.data;
};

export const updateProfile = async (data: Partial<UserProfile> & { currentPassword?: string; newPassword?: string }): Promise<UserProfile> => {
  const res = await api.put("/users/profile", data);
  return res.data;
};

export const uploadProfileImage = async (file: File): Promise<UserProfile> => {
  const formData = new FormData();
  formData.append("file", file);
  const res = await api.post("/users/profile/image", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
};

export const removeProfileImage = async (): Promise<UserProfile> => {
  const res = await api.delete("/users/profile/image");
  return res.data;
};

export const changeAccountPassword = async (data: { currentPassword: string; newPassword: string }) => {
  const res = await api.put("/users/password", data);
  return res.data;
};

export const getPreferences = async (): Promise<UserPreferences> => {
  const res = await api.get("/users/preferences");
  return res.data;
};

export const updatePreferences = async (data: Partial<UserPreferences>): Promise<UserPreferences> => {
  const res = await api.put("/users/preferences", data);
  return res.data;
};

export const getUserSettings = async (): Promise<UserProfile> => {
  const res = await api.get("/users/settings");
  return res.data;
};

// ============================================================
// PRODUCTS APIs
// ============================================================

export interface ProductQueryParams {
  search?: string;
  category?: string;
  brand?: string;
  min_price?: number;
  max_price?: number;
  min_ram?: number;
  min_rating?: number;
  sort?: "match" | "score" | "price-low" | "price-high" | "rating";
  page?: number;
  limit?: number;
}

export interface ProductListResponseData {
  items: Product[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

export const getProducts = async (params: ProductQueryParams = {}): Promise<ProductListResponseData> => {
  const res = await api.get("/products", { params });
  return res.data;
};

export const getProductById = async (id: string): Promise<Product> => {
  const res = await api.get(`/products/${encodeURIComponent(id)}`);
  return res.data;
};

export const getFilterMeta = async () => {
  const res = await api.get("/products/filters/meta");
  return res.data;
};

// ============================================================
// RECOMMENDATION APIs
// ============================================================

export interface RecommendedItem {
  rank: number;
  match_score: number;
  product: Product;
  reason: string;
  strengths: string[];
  weaknesses: string[];
}

export interface RecommendationResponseData {
  query: string;
  nlp_extracted: any;
  recommendations: RecommendedItem[];
  explanation: string;
  summary?: string;
}

export const getRecommendations = async (query: string, category = "Laptop", top_k = 5): Promise<RecommendationResponseData> => {
  const res = await api.post("/recommendations", { query, category, top_k });
  return res.data;
};

export const getPersonalizedRecommendations = async (): Promise<{
  personalized_for: string;
  preferences_applied: any;
  recommendations: RecommendedItem[];
  explanation: string;
}> => {
  const res = await api.get("/recommendations/personalized");
  return res.data;
};

// ============================================================
// COMPARISON API
// ============================================================

export interface SpecComparisonRow {
  label: string;
  key?: string;
  category?: string;
  values?: Record<string, any>;
  winner_id?: string | null;
  winner_product_id?: string | null;
  is_different?: boolean;
}

export interface CompareResponseData {
  products?: Product[];
  comparison_matrix?: SpecComparisonRow[];
  spec_rows?: SpecComparisonRow[];
  summary?: string;
  winner_summary?: string;
  value_winner?: {
    id: string;
    name: string;
    reason: string;
  };
  performance_winner?: {
    id: string;
    name: string;
    reason: string;
  };
}

export const compareProducts = async (product_ids: string[]): Promise<CompareResponseData> => {
  const res = await api.post<CompareResponseData>("/compare", { product_ids });
  return res.data;
};

// ============================================================
// AI CHAT API
// ============================================================

export interface ChatRequestParams {
  message: string;
  history?: Array<{ role: string; content: string }>;
  shortlisted_ids?: string[];
  context_products?: Array<{ index?: number; id?: any; product_id?: any; name?: string }>;
  selected_products?: any[];
  battle_result?: any;
  current_page_context?: string;
  active_product_id?: string | number;
  session_id?: string;
  conversation_id?: string;
}

export interface SourceCitation {
  filename: string;
  page_number?: number;
  section_title?: string;
  snippet: string;
  score?: number;
}

export interface ChatResponseData {
  message: string;
  answer?: string;
  intent: string;
  type?: "specification" | "comparison" | "recommendation" | "document" | "explanation" | "general" | string;
  field?: string;
  verified?: boolean;
  source_type?: "database" | "documents" | "hybrid" | "general" | string;
  product?: Product | any;
  products: Product[];
  compared_products?: any[];
  ignored_products?: any[];
  recommendations: RecommendedItem[];
  comparison?: any;
  rag_sources: Array<{ filename: string; snippet: string; score: number; page_number?: number; section_title?: string }>;
  sources: SourceCitation[];
  suggested_followups: string[];
  confidence: "high" | "medium" | "low";
  context_used: "database" | "documents" | "hybrid" | "general";
  show_recommendations?: boolean;
  show_comparison?: boolean;
  show_sources?: boolean;
  session_id?: string;
  conversation_id?: string;
  debug_trace?: any;
  response_mode?: "FAST" | "AI" | "RAG" | string;
}

export const sendChatMessage = async (params: ChatRequestParams): Promise<ChatResponseData> => {
  const res = await api.post("/chat", params);
  return res.data;
};

export const analyzeNLP = async (message: string) => {
  const res = await api.post("/nlp/analyze", { message });
  return res.data;
};

export const searchRAG = async (query: string, top_k = 5) => {
  const res = await api.post("/rag/search", { query, top_k });
  return res.data;
};

// ============================================================
// TEMPORARY SESSION PERSISTENCE APIs
// ============================================================

export interface SaveSessionPayload {
  conversation_id: string;
  comparison_products?: any[];
  selected_products?: any[];
  active_product?: any;
  messages?: any[];
  last_intent?: string;
  metadata?: Record<string, any>;
}

export interface BackendSessionData {
  conversation_id: string;
  comparison_products: Product[];
  selected_products: Product[];
  active_product?: Product | null;
  messages: Array<{ id?: string; role: string; content: string; timestamp?: any }>;
  last_intent?: string;
  active_category?: string;
  created_at: string;
  expires_at: string;
}

export const saveBackendSession = async (payload: SaveSessionPayload): Promise<{ status: string; conversation_id: string }> => {
  const res = await api.post("/session/save", payload);
  return res.data;
};

export const getBackendSession = async (conversation_id: string): Promise<BackendSessionData> => {
  const res = await api.get(`/session/${encodeURIComponent(conversation_id)}`);
  return res.data;
};

export const deleteBackendSession = async (conversation_id: string): Promise<{ status: string }> => {
  const res = await api.delete(`/session/${encodeURIComponent(conversation_id)}`);
  return res.data;
};

// ============================================================
// FAVORITES / WISHLIST APIs
// ============================================================

export const getFavorites = async (): Promise<{ items: Product[]; total: number }> => {
  const res = await api.get("/favorites");
  return res.data;
};

export const addFavorite = async (product_id: string) => {
  const res = await api.post("/favorites", { product_id });
  return res.data;
};

export const removeFavorite = async (product_id: string) => {
  const res = await api.delete(`/favorites/${encodeURIComponent(product_id)}`);
  return res.data;
};

// ============================================================
// HISTORY APIs
// ============================================================

export const getHistory = async () => {
  const res = await api.get("/history");
  return res.data;
};

export const deleteHistoryItem = async (id: number, type: "search" | "comparison" = "search") => {
  const res = await api.delete(`/history/${id}?history_type=${type}`);
  return res.data;
};

export const clearAllHistory = async () => {
  const res = await api.delete("/history");
  return res.data;
};

// ============================================================
// DOCUMENTS & RAG APIs
// ============================================================

export interface DocumentItem {
  id: number;
  filename: string;
  file_type: string;
  file_size: number;
  status: "uploading" | "processing" | "indexing" | "indexed" | "failed";
  chunk_count: number;
  product_name?: string;
  category?: string;
  summary?: string;
  created_at: string;
}

export interface DocumentQueryResult {
  chunk_id: number;
  document_id: number;
  filename: string;
  content: string;
  similarity_score: number;
  page_number?: number;
  section_title?: string;
  product_name?: string;
}

export interface DocumentQueryResponse {
  query: string;
  results: DocumentQueryResult[];
  answer: string;
  confidence: string;
  context_used: string;
  sources: SourceCitation[];
}

export const getDocuments = async (): Promise<DocumentItem[]> => {
  const res = await api.get("/documents");
  return res.data;
};

export const uploadDocument = async (file: File): Promise<DocumentItem> => {
  const formData = new FormData();
  formData.append("file", file);
  const res = await api.post("/documents/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
};

export interface RAGChatRequestParams {
  message: string;
  document_id?: number;
  document_ids?: number[];
  product_name?: string;
  category?: string;
  history?: Array<{ role: string; content: string }>;
  top_k?: number;
}

export interface RAGChatSource {
  document: string;
  page?: number | string;
  section?: string;
  snippet?: string;
  score?: number;
}

export interface RAGChatResponseData {
  answer: string;
  sources: RAGChatSource[];
  confidence: "High" | "Medium" | "Low" | string;
  rag_version: string;
  document_used: boolean;
  type?: string;
  suggested_followups?: string[];
  debug_trace?: Record<string, any>;
}

export const sendRAGChatMessage = async (params: RAGChatRequestParams): Promise<RAGChatResponseData> => {
  const res = await api.post("/rag/chat", params);
  return res.data;
};

export const queryDocuments = async (query: string, document_ids?: number[]): Promise<DocumentQueryResponse> => {
  const res = await api.post("/documents/query", { query, document_ids });
  return res.data;
};

export const deleteDocument = async (id: number) => {
  const res = await api.delete(`/documents/${id}`);
  return res.data;
};

// ============================================================
// FEEDBACK API
// ============================================================

export const submitFeedback = async (data: {
  recommendation_id?: number;
  product_id?: string;
  rating: string;
  reason?: string;
}) => {
  const res = await api.post("/feedback", data);
  return res.data;
};

// ============================================================
// DASHBOARD & ADMIN ANALYTICS APIs
// ============================================================

export interface DashboardStats {
  total_products: number;
  laptop_count?: number;
  phone_count?: number;
  tablet_count?: number;
  wishlist_count: number;
  comparison_count: number;
  recommendation_count: number;
  recent_search_count: number;
  document_count?: number;
  unread_notifications?: number;
  profile_completion_score?: number;
}

export interface AIInsights {
  most_viewed_category: string;
  preferred_budget: string;
  favorite_brand: string;
  performance_priority: string;
  ai_profile_score: number;
}

export interface ActivityTimelineItem {
  id: string;
  type: "comparison" | "document" | "chat" | "wishlist";
  title: string;
  description: string;
  time_label: string;
  created_at: string;
  target?: string;
}

export interface CategoryDistributionItem {
  category: string;
  count: number;
  percentage: number;
  color?: string;
}

export interface PriceSegmentItem {
  range: string;
  count: number;
  segment?: string;
}

export interface BrandShareItem {
  name: string;
  count: number;
  percentage?: number;
}

export const getDashboardStats = async (): Promise<DashboardStats> => {
  const res = await api.get("/dashboard/stats");
  return res.data;
};

export const getDashboardInsights = async (): Promise<AIInsights> => {
  const res = await api.get("/dashboard/insights");
  return res.data;
};

export const getActivityTimeline = async (): Promise<ActivityTimelineItem[]> => {
  const res = await api.get("/dashboard/timeline");
  return res.data;
};

export const getCategoryDistribution = async (): Promise<CategoryDistributionItem[]> => {
  const res = await api.get("/dashboard/category-distribution");
  return res.data;
};

export const getPriceSegmentation = async (category?: string): Promise<PriceSegmentItem[]> => {
  const res = await api.get("/dashboard/price-segmentation", { params: category ? { category } : {} });
  return res.data;
};

export const getBrandMarketShare = async (category?: string): Promise<BrandShareItem[]> => {
  const res = await api.get("/dashboard/brand-market-share", { params: category ? { category } : {} });
  return res.data;
};

export const getDashboardAnalytics = async () => {
  const res = await api.get("/dashboard/analytics");
  return res.data;
};

export const getAdminAnalytics = async () => {
  const res = await api.get("/admin/analytics");
  return res.data;
};

export const getAdminUsers = async () => {
  const res = await api.get("/admin/users");
  return res.data;
};

export const getAdminProducts = async (params: { search?: string; page?: number; limit?: number } = {}) => {
  const res = await api.get("/admin/products", { params });
  return res.data;
};

export const createAdminProduct = async (productData: any) => {
  const res = await api.post("/admin/products", productData);
  return res.data;
};

export const updateAdminProduct = async (id: string, productData: any) => {
  const res = await api.put(`/admin/products/${encodeURIComponent(id)}`, productData);
  return res.data;
};

export const deleteAdminProduct = async (id: string) => {
  const res = await api.delete(`/admin/products/${encodeURIComponent(id)}`);
  return res.data;
};

export const importAdminCSV = async (file?: File) => {
  if (file) {
    const formData = new FormData();
    formData.append("file", file);
    const res = await api.post("/admin/products/import-csv", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return res.data;
  }
  const res = await api.post("/admin/products/import-csv");
  return res.data;
};

export const getDataQualityReport = async () => {
  const res = await api.get("/chat/data-quality");
  return res.data;
};

// ============================================================
// MULTI-USER DATABASE PERSISTENCE APIs (CHAT, COMPARISONS, CONTEXT)
// ============================================================

export interface UserConversationSummary {
  conversation_id: string;
  title: string;
  last_message: string;
  last_role: string;
  message_count: number;
  last_intent: string;
  products_discussed: string[];
  updated_at: string;
}

export const getUserConversations = async (): Promise<UserConversationSummary[]> => {
  const res = await api.get("/chat/conversations");
  return res.data;
};

export const getConversationMessages = async (conversationId: string): Promise<any[]> => {
  const res = await api.get(`/chat/conversations/${encodeURIComponent(conversationId)}`);
  return res.data;
};

export const deleteUserConversation = async (conversationId: string) => {
  const res = await api.delete(`/chat/conversations/${encodeURIComponent(conversationId)}`);
  return res.data;
};

export const getUserConversationContext = async (conversationId: string) => {
  const res = await api.get(`/chat/context/${encodeURIComponent(conversationId)}`);
  return res.data;
};

export const saveUserConversationContext = async (
  conversationId: string,
  activeProducts: any[],
  selectedProducts: any[] = [],
  lastIntent: string = "general"
) => {
  const res = await api.post("/chat/context", {
    conversation_id: conversationId,
    active_products: activeProducts,
    selected_products: selectedProducts,
    last_intent: lastIntent,
  });
  return res.data;
};

export interface SavedComparisonItem {
  id: number;
  comparison_id: string;
  product_ids: any[];
  comparison_result: any;
  summary?: string;
  created_at: string;
}

export const getUserSavedComparisons = async (): Promise<SavedComparisonItem[]> => {
  const res = await api.get("/compare/saved");
  return res.data;
};

export const saveUserComparison = async (
  comparisonId: string,
  productIds: any[],
  comparisonResult?: any
) => {
  const res = await api.post("/compare/save", {
    comparison_id: comparisonId,
    product_ids: productIds,
    comparison_result: comparisonResult,
  });
  return res.data;
};

export const deleteUserSavedComparison = async (comparisonId: string) => {
  const res = await api.delete(`/compare/saved/${encodeURIComponent(comparisonId)}`);
  return res.data;
};

// ============================================================
// NOTIFICATIONS APIs
// ============================================================

export const getNotifications = async (
  status?: string,
  limit: number = 50,
  offset: number = 0
): Promise<NotificationListResponse> => {
  const params: any = { limit, offset };
  if (status) params.status = status;
  const res = await api.get("/notifications", { params });
  return res.data;
};

export const getUnreadNotificationCount = async (): Promise<number> => {
  const res = await api.get("/notifications/unread-count");
  return res.data?.count ?? 0;
};

export const markNotificationRead = async (id: number) => {
  const res = await api.post(`/notifications/read/${id}`);
  return res.data;
};

export const markAllNotificationsRead = async () => {
  const res = await api.post("/notifications/read-all");
  return res.data;
};

export const deleteNotification = async (id: number) => {
  const res = await api.delete(`/notifications/${id}`);
  return res.data;
};

export const clearAllNotifications = async () => {
  const res = await api.delete("/notifications");
  return res.data;
};

// ============================================================
// AI PRODUCT BATTLE APIs
// ============================================================

export const runProductBattle = async (
  productIds: (number | string)[]
): Promise<BattleResultData> => {
  const res = await api.post("/product/battle", { product_ids: productIds });
  return res.data;
};

export const getBattleHistory = async (
  limit: number = 20,
  offset: number = 0
): Promise<BattleHistoryResponse> => {
  const res = await api.get("/product/battle/history", { params: { limit, offset } });
  return res.data;
};

export const getBattleDetail = async (
  battleId: number
): Promise<{ success: boolean; battle: BattleResultData }> => {
  const res = await api.get(`/product/battle/${battleId}`);
  return res.data;
};

export default api;

