/**
 * Product Image and Spec Helper Utility
 * Provides reliable image resolution with category-specific fallbacks
 * and eliminates NaN RAM display bugs.
 */

const CATEGORY_FALLBACKS: Record<string, string> = {
  laptop: "https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?w=600&auto=format&fit=crop&q=80",
  phone: "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=600&auto=format&fit=crop&q=80",
  smartphone: "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=600&auto=format&fit=crop&q=80",
  tablet: "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=600&auto=format&fit=crop&q=80",
  default: "https://images.unsplash.com/photo-1526738549149-8e07eca6c147?w=600&auto=format&fit=crop&q=80",
};

/**
 * Returns a guaranteed valid image URL for any product object.
 * Checks image_url, image, image_path and provides clean category fallbacks.
 */
export function getProductImage(product?: any): string {
  if (!product) {
    return CATEGORY_FALLBACKS.default;
  }

  const category = (product.category || "").toLowerCase().trim();
  const fallback = CATEGORY_FALLBACKS[category] || CATEGORY_FALLBACKS.default;

  const candidate = product.image_url || product.image || product.image_path || product.imageUrl;

  if (typeof candidate === "string" && candidate.trim().length > 5) {
    const trimmed = candidate.trim();
    if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
      return trimmed;
    }
    if (trimmed.startsWith("/")) {
      const backendUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/api$/, "") || "http://localhost:8000";
      return `${backendUrl}${trimmed}`;
    }
  }

  return fallback;
}

/**
 * Formats RAM value safely, preventing 'NaN RAM' displays.
 * If missing, returns 'Not available'.
 */
export function formatRamDisplay(ram?: any): string {
  if (ram === undefined || ram === null || ram === "" || (typeof ram === "number" && isNaN(ram))) {
    return "Not available";
  }
  const str = String(ram).trim();
  if (str.toLowerCase() === "nan" || str === "0" || str === "") {
    return "Not available";
  }
  if (!str.toLowerCase().includes("gb") && !isNaN(Number(str))) {
    return `${str}GB`;
  }
  return str;
}
