/**
 * Individual fashion item result from a visual similarity search.
 */
export interface ChicFinderResult {
  image_id: string;
  similarity_score: number;
  brand?: string;
  price_egp?: number;
  product_url?: string;
  store_location?: string;
  image_url?: string;
  availability_egypt: boolean;
}

export interface SearchResponse {
  results: ChicFinderResult[];
  processing_time_ms: number;
}

export interface SearchRequest {
  image_base64: string;
  top_k: number;
}

// ---------------------------------------------------------------------------
// Stores
// ---------------------------------------------------------------------------

export interface Store {
  id: string;
  name: string;
  description: string;
  logo_url?: string;
  website_url?: string;
  location?: string;
  categories: string[];
}

export interface StoreItem {
  id: string;
  name: string;
  brand: string;
  category: string;
  type: string;
  color: string;
  price_egp: number;
  sizes: string[];
  image_url?: string;
  product_url?: string;
  description?: string;
  store_id: string;
  store_location?: string;
}

export interface StoreDetailResponse {
  store: Store;
  items: StoreItem[];
  total_items: number;
}
