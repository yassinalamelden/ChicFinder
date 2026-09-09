/**
 * Response shapes returned by the ChicFinder FastAPI backend.
 * Mirrors api/models/schemas.py, api/routes/saved.py and api/routes/account.py.
 */

export interface ChicFinderResult {
  image_id: string;
  similarity_score: number;
  brand?: string;
  title?: string;
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

export interface Store {
  id: string;
  name: string;
  description?: string;
  logo_url?: string;
  website_url?: string;
  location?: string;
  categories: string[];
}

export interface StoreItem {
  id: string;
  name: string;
  brand?: string;
  category?: string;
  type?: string;
  color?: string;
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

export interface SavedItem {
  id: string;
  name?: string | null;
  brand?: string | null;
  category?: string | null;
  price_egp?: number | null;
  image_url?: string | null;
  product_url?: string | null;
  store_id?: string | null;
  store_location?: string | null;
}

export interface SavedItemsResponse {
  items: SavedItem[];
  total: number;
}

export interface SavedIdsResponse {
  ids: string[];
}

export interface DeletionResponse {
  deleted: boolean;
  rows_removed: number;
  auth_record_removed: boolean;
  message: string;
}
