export interface Product {
  id: string;
  numeric_id?: number;
  brand: string;
  name: string;
  category: string;
  model?: string;
  price: number;
  original_price?: number;
  cpu: string;
  ram: number;
  storage: string;
  gpu?: string;
  score: number;
  image: string;
  image_url?: string;
  image_path?: string;
  rating?: number;
  reviews?: number;
  badge?: string;
  specsSummary?: string;
  pros?: string[];
  cons?: string[];
  fpsData?: { game: string; fps: number; resolution: string }[];
  specs?: {
    cpu?: string;
    ram_gb?: number;
    storage?: string;
    gpu?: string;
    display_size_inch?: number;
    resolution?: string;
    os?: string;
    weight_kg?: number;
    battery?: string;
    base_clock_speed_ghz?: number;
    touch_screen?: boolean;
    ports?: string;
    raw_specs?: Record<string, any>;
  };
}

export interface UserPreferences {
  defaultCategory: string;
  aiStyle: "balanced" | "performance" | "budget" | "battery";
  currency: "INR" | "USD" | "EUR";
  notificationsEmail: boolean;
  notificationsPriceDrops: boolean;
  darkMode: boolean;
  budgetMin?: number;
  budgetMax?: number;
  preferredBrands?: string[];
  priorityFeatures?: string[];
}

export interface PriceAlert {
  id: string;
  productId: string;
  productName: string;
  targetPrice: number;
  currentPrice: number;
  createdAt: string;
  triggered?: boolean;
}

export interface UserProfile {
  id?: number;
  name: string;
  email: string;
  avatar?: string;
  profile_image?: string;
  title?: string;
  phone?: string;
  location?: string;
  bio?: string;
  authMethod: "local" | "google" | "local+google" | "email" | "github" | string;
  twoFactorEnabled?: boolean;
  isAdmin?: boolean;
  role?: string;
  totalChats?: number;
  totalConversations?: number;
  totalComparisons?: number;
  wishlistCount?: number;
  preferences: UserPreferences;
}

export interface AppNotification {
  id: number;
  user_id: number;
  title: string;
  message: string;
  type: "AUTH" | "AI_CHAT" | "RAG" | "COMPARISON" | "PRODUCT" | "SYSTEM" | string;
  status: "unread" | "read";
  reference_id?: string | null;
  created_at: string;
  read_at?: string | null;
}

export interface NotificationListResponse {
  success: boolean;
  notifications: AppNotification[];
  total: number;
  unread_count: number;
}

export interface BattleRound {
  round_number: number;
  title: string;
  icon: string;
  weight: string;
  p1_score: number;
  p2_score: number;
  p1_metrics: Record<string, any>;
  p2_metrics: Record<string, any>;
  winner: "p1" | "p2" | "tie";
  winner_name: string;
  reason: string;
}

export interface BattleAIVerdict {
  summary: string;
  performance_winner: string;
  performance_reason: string;
  price_winner: string;
  price_reason: string;
  final_winner: string;
  final_winner_id?: string | number | null;
  confidence_score: string;
  key_reasons: string[];
}

export interface BattleResultData {
  battle_id?: number | null;
  product_1: Product;
  product_2: Product;
  product_1_name: string;
  product_2_name: string;
  product_1_score: number;
  product_2_score: number;
  winner_id?: string | number | null;
  winner_name: string;
  winner_score: number;
  rounds: BattleRound[];
  ai_verdict: BattleAIVerdict;
  key_reasons: string[];
  confidence: string;
  markdown?: string;
  created_at?: string;
}

export interface BattleHistoryResponse {
  success: boolean;
  total: number;
  battles: BattleResultData[];
}

