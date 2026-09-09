/**
 * Client for the ChicFinder FastAPI backend.
 *
 * Every authenticated call attaches the current Firebase ID token. Requests
 * carry a timeout because the /recommend path runs FashionCLIP plus two Gemini
 * calls and can legitimately take several seconds, but should not hang a phone
 * screen forever on a flaky connection.
 */

import Constants from "expo-constants";
import { auth } from "./firebase";
import type {
  DeletionResponse,
  SavedIdsResponse,
  SavedItemsResponse,
  SearchResponse,
  Store,
  StoreDetailResponse,
  StoreItem,
  ChicFinderResult,
} from "../types/api";

const extra = (Constants.expoConfig?.extra ?? {}) as Record<string, string>;

export const BASE_URL =
  process.env.EXPO_PUBLIC_API_URL ?? extra.apiUrl ?? "http://localhost:8000";

/** Search hits the model pipeline, so it gets a longer budget than plain reads. */
const SEARCH_TIMEOUT_MS = 60_000;
const DEFAULT_TIMEOUT_MS = 15_000;

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function getToken(): Promise<string> {
  const user = auth.currentUser;
  if (!user) throw new ApiError("You need to be signed in to do that.", 401);
  return user.getIdToken();
}

interface RequestOptions extends RequestInit {
  timeoutMs?: number;
  auth?: boolean;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, auth: needsAuth = true, ...init } = options;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  const headers: Record<string, string> = { ...(init.headers as Record<string, string>) };
  if (needsAuth) headers.Authorization = `Bearer ${await getToken()}`;

  try {
    const res = await fetch(`${BASE_URL}${path}`, {
      ...init,
      headers,
      signal: controller.signal,
    });

    if (!res.ok) {
      const detail = await res.json().catch(() => null);
      throw new ApiError(
        (detail && (detail.detail as string)) || httpMessage(res.status),
        res.status
      );
    }

    if (res.status === 204) return undefined as T;
    return (await res.json()) as T;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    if ((err as Error).name === "AbortError") {
      throw new ApiError("That took too long. Check your connection and try again.");
    }
    throw new ApiError("Could not reach ChicFinder. Check your connection.");
  } finally {
    clearTimeout(timer);
  }
}

function httpMessage(status: number): string {
  if (status === 401) return "Your session expired. Please sign in again.";
  if (status === 404) return "We could not find that.";
  if (status === 503) return "ChicFinder is busy right now. Please try again shortly.";
  if (status >= 500) return "Something went wrong on our side. Please try again.";
  return `Request failed (${status}).`;
}

/** Turns a relative image path from the API into a URL the app can load. */
export function resolveImageUrl(url?: string | null): string | undefined {
  if (!url) return undefined;
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  // The backend sometimes returns a Windows-style path from the ingest script.
  const filename = url.replace(/\\/g, "/").split("/").pop();
  if (!filename) return undefined;
  return `${BASE_URL}/images/${filename}`;
}

// ---------------------------------------------------------------------------
// Visual search
// ---------------------------------------------------------------------------

interface RecommendPayload {
  recommendations?: Array<{
    recommendations?: Array<{
      id: string;
      image_url?: string;
      brand?: string;
      title?: string;
      price?: string | number;
      category?: string;
      product_url?: string;
    }>;
  }>;
}

/**
 * Uploads a photo to /recommend and normalises the nested response into the
 * flat result list the UI renders.
 */
export async function searchByPhoto(
  uri: string,
  mimeType = "image/jpeg"
): Promise<SearchResponse> {
  const form = new FormData();
  form.append("file", {
    uri,
    name: `outfit.${mimeType.split("/")[1] ?? "jpg"}`,
    type: mimeType,
    // React Native's FormData accepts this shape; the DOM types do not describe it.
  } as unknown as Blob);

  const start = Date.now();
  const data = await request<RecommendPayload>("/api/v1/recommend", {
    method: "POST",
    body: form,
    timeoutMs: SEARCH_TIMEOUT_MS,
  });

  const raw = data.recommendations?.[0]?.recommendations ?? [];

  const results: ChicFinderResult[] = raw.map((item) => {
    const price =
      typeof item.price === "number" ? item.price : parseFloat(item.price ?? "");
    return {
      image_id: item.id,
      similarity_score: 1,
      brand: item.brand,
      title: item.title,
      price_egp: Number.isNaN(price) ? undefined : price,
      product_url: item.product_url,
      image_url: resolveImageUrl(item.image_url),
      availability_egypt: true,
    };
  });

  return { results, processing_time_ms: Date.now() - start };
}

// ---------------------------------------------------------------------------
// Stores (public)
// ---------------------------------------------------------------------------

export function getStores(): Promise<Store[]> {
  return request<Store[]>("/api/v1/stores", { auth: false });
}

export function getStoreDetail(storeId: string): Promise<StoreDetailResponse> {
  return request<StoreDetailResponse>(`/api/v1/stores/${storeId}`, { auth: false });
}

export function getStoreItems(
  storeId: string,
  opts: { category?: string; search?: string } = {}
): Promise<StoreItem[]> {
  const params = new URLSearchParams();
  if (opts.category) params.set("category", opts.category);
  if (opts.search) params.set("search", opts.search);
  const qs = params.toString() ? `?${params}` : "";
  return request<StoreItem[]>(`/api/v1/stores/${storeId}/items${qs}`, { auth: false });
}

// ---------------------------------------------------------------------------
// Saved items
// ---------------------------------------------------------------------------

export function getSavedItems(): Promise<SavedItemsResponse> {
  return request<SavedItemsResponse>("/api/v1/saved");
}

export function getSavedIds(): Promise<SavedIdsResponse> {
  return request<SavedIdsResponse>("/api/v1/saved/ids");
}

export function saveItem(itemId: string): Promise<void> {
  return request<void>(`/api/v1/saved/${encodeURIComponent(itemId)}`, { method: "PUT" });
}

export function unsaveItem(itemId: string): Promise<void> {
  return request<void>(`/api/v1/saved/${encodeURIComponent(itemId)}`, {
    method: "DELETE",
  });
}

// ---------------------------------------------------------------------------
// Account
// ---------------------------------------------------------------------------

export function deleteAccount(): Promise<DeletionResponse> {
  return request<DeletionResponse>("/api/v1/account", {
    method: "DELETE",
    timeoutMs: 30_000,
  });
}
