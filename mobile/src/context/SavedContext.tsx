/**
 * Saved items (wishlist) state.
 *
 * The heart on a product card has to feel instant, so a toggle updates local
 * state first and reverts if the server rejects it. The set of saved IDs is
 * loaded once per sign-in and kept in memory, which keeps every card render
 * free of a network call.
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import * as api from "../lib/api";
import type { SavedItem } from "../types/api";
import { useAuth } from "./AuthContext";

interface SavedContextValue {
  savedIds: Set<string>;
  items: SavedItem[];
  loading: boolean;
  error: string | null;
  isSaved: (itemId: string) => boolean;
  toggleSaved: (itemId: string) => Promise<void>;
  refresh: () => Promise<void>;
}

const SavedContext = createContext<SavedContextValue | null>(null);

export function SavedProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [savedIds, setSavedIds] = useState<Set<string>>(new Set());
  const [items, setItems] = useState<SavedItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!user) {
      setSavedIds(new Set());
      setItems([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await api.getSavedItems();
      setItems(data.items);
      setSavedIds(new Set(data.items.map((item) => item.id)));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, [user]);

  // Reload on sign-in, clear on sign-out.
  useEffect(() => {
    refresh();
  }, [refresh]);

  const isSaved = useCallback((itemId: string) => savedIds.has(itemId), [savedIds]);

  const toggleSaved = useCallback(
    async (itemId: string) => {
      if (!user) throw new Error("Sign in to save items.");

      const wasSaved = savedIds.has(itemId);

      // Optimistic update.
      setSavedIds((prev) => {
        const next = new Set(prev);
        wasSaved ? next.delete(itemId) : next.add(itemId);
        return next;
      });

      try {
        if (wasSaved) {
          await api.unsaveItem(itemId);
          setItems((prev) => prev.filter((item) => item.id !== itemId));
        } else {
          await api.saveItem(itemId);
          // Pull the enriched row so the Saved tab shows real metadata.
          refresh();
        }
      } catch (err) {
        // Put it back the way it was, then let the caller surface the failure.
        setSavedIds((prev) => {
          const next = new Set(prev);
          wasSaved ? next.add(itemId) : next.delete(itemId);
          return next;
        });
        throw err;
      }
    },
    [user, savedIds, refresh]
  );

  const value = useMemo<SavedContextValue>(
    () => ({ savedIds, items, loading, error, isSaved, toggleSaved, refresh }),
    [savedIds, items, loading, error, isSaved, toggleSaved, refresh]
  );

  return <SavedContext.Provider value={value}>{children}</SavedContext.Provider>;
}

export function useSaved(): SavedContextValue {
  const ctx = useContext(SavedContext);
  if (!ctx) throw new Error("useSaved must be used inside a SavedProvider.");
  return ctx;
}
