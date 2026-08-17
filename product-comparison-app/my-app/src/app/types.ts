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
