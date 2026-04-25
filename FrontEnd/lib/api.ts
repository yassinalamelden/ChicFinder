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
// Recommendation
// ---------------------------------------------------------------------------

export async function postRecommend(file: File): Promise<SearchResponse> {
  const form = new FormData();
  form.append("file", file);

  const start = Date.now();
  const res = await authFetch("/api/v1/recommend", {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail?.detail ?? `HTTP ${res.status}`);
  }

  const data = await res.json();

  // Transform /recommend response shape into SearchResponse
  const rawItems: Array<{ id: string; image_url?: string; brand?: string; price?: string | number; category?: string }> =
    data.recommendations?.[0]?.recommendations ?? [];

  const results: ChicFinderResult[] = rawItems.map((item) => {
    const rawUrl = item.image_url ?? "";
    const filename = rawUrl.replace(/\\/g, "/").split("/").pop() ?? "";
    const price = typeof item.price === "number" ? item.price : parseFloat(item.price ?? "");

    return {
      image_id: item.id,
      similarity_score: 1,
      brand: item.brand,
      price_egp: isNaN(price) ? undefined : price,
      image_url: filename ? `${BASE_URL}/images/${filename}` : undefined,
      availability_egypt: true,
    };
  });

  return { results, processing_time_ms: Date.now() - start };
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
