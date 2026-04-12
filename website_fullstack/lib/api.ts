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

  const res = await authFetch("/api/v1/recommend", {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail?.detail ?? `HTTP ${res.status}`);
  }

  return res.json() as Promise<SearchResponse>;
}

// ---------------------------------------------------------------------------
// Stores
// ---------------------------------------------------------------------------

export async function getStores(): Promise<Store[]> {
  const res = await authFetch("/api/v1/stores");
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<Store[]>;
}

export async function getStoreDetail(storeId: string): Promise<StoreDetailResponse> {
  const res = await authFetch(`/api/v1/stores/${storeId}`);
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

  const res = await authFetch(`/api/v1/stores/${storeId}/items${qs}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<StoreItem[]>;
}
