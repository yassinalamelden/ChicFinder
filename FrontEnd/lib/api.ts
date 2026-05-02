/**
 * API client for ChicFinder backend.
 * All requests are authenticated with a Firebase ID token.
 */

import { auth } from "@/lib/firebase";
import type {
  SearchResponse,
  Store,
  StoreDetailResponse,
  StoreItem,
} from "@/types/api";

type SearchFilters = {
  min_price?: number;
  max_price?: number;
  brands?: string[];
};

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function getToken(): Promise<string> {
  const user = auth.currentUser;
  if (!user) throw new Error("Not authenticated");
  return user.getIdToken();
}

async function authFetch(path: string, init?: RequestInit): Promise<Response> {
  const token = await getToken();
  return fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${token}`,
      ...init?.headers,
    },
  });
}

// ---------------------------------------------------------------------------
// Search (primary — uses real AI engine via /api/v1/search)
// ---------------------------------------------------------------------------

export async function searchByImage(
  file: File,
  filters?: SearchFilters
): Promise<SearchResponse> {
  const buffer = await file.arrayBuffer();
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  const image_base64 = btoa(binary);

  const res = await authFetch("/api/v1/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image_base64, top_k: 10, ...filters }),
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail?.detail ?? `HTTP ${res.status}`);
  }

  return res.json() as Promise<SearchResponse>;
}

// ---------------------------------------------------------------------------
// Stores (public — no auth token required)
// ---------------------------------------------------------------------------

export async function getStores(): Promise<Store[]> {
  const res = await fetch(`${BASE_URL}/api/v1/stores`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<Store[]>;
}

export async function getStoreDetail(storeId: string): Promise<StoreDetailResponse> {
  const res = await fetch(`${BASE_URL}/api/v1/stores/${storeId}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<StoreDetailResponse>;
}

export async function getStoreItems(
  storeId: string,
  category?: string,
  search?: string
): Promise<StoreItem[]> {
  const params = new URLSearchParams();
  if (category) params.set("category", category);
  if (search) params.set("search", search);
  const qs = params.toString() ? `?${params}` : "";

  const res = await fetch(`${BASE_URL}/api/v1/stores/${storeId}/items${qs}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<StoreItem[]>;
}
