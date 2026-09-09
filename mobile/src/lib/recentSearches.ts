/**
 * Recently searched photos, kept on the device.
 *
 * Stores the local image URI rather than a copy, so this costs almost nothing.
 * The trade-off is that a URI can go stale: a camera shot lives in the app's
 * cache and the OS may reclaim it, and a library asset can be deleted. Callers
 * must therefore treat a thumbnail that fails to load as a normal outcome, and
 * `drop` exists so a re-run that 404s can quietly remove the entry.
 *
 * Deliberately not synced to the account: this is a convenience for getting back
 * to a photo you just took, not a history feature.
 */

import AsyncStorage from "@react-native-async-storage/async-storage";

const KEY = "chicfinder.recentSearches";
const LIMIT = 12;

export interface RecentSearch {
  /** Local file URI of the photo that was searched. */
  uri: string;
  /** Epoch milliseconds, so the list can stay newest-first. */
  at: number;
  /** How many matches came back, shown as a small caption. */
  count: number;
}

function parse(raw: string | null): RecentSearch[] {
  if (!raw) return [];
  try {
    const value = JSON.parse(raw);
    if (!Array.isArray(value)) return [];
    return value.filter(
      (entry): entry is RecentSearch =>
        typeof entry?.uri === "string" &&
        typeof entry?.at === "number" &&
        typeof entry?.count === "number"
    );
  } catch {
    // Corrupt storage should reset the list, not crash the screen.
    return [];
  }
}

export async function loadRecent(): Promise<RecentSearch[]> {
  try {
    return parse(await AsyncStorage.getItem(KEY));
  } catch {
    return [];
  }
}

/** Adds a search to the front, de-duplicating by URI. */
export async function addRecent(uri: string, count: number): Promise<RecentSearch[]> {
  const existing = await loadRecent();
  const next: RecentSearch[] = [
    { uri, at: Date.now(), count },
    ...existing.filter((entry) => entry.uri !== uri),
  ].slice(0, LIMIT);

  try {
    await AsyncStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    // Losing the write is not worth interrupting a successful search.
  }
  return next;
}

/** Removes one entry, for when its photo no longer exists. */
export async function dropRecent(uri: string): Promise<RecentSearch[]> {
  const next = (await loadRecent()).filter((entry) => entry.uri !== uri);
  try {
    await AsyncStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    /* ignore */
  }
  return next;
}

export async function clearRecent(): Promise<void> {
  try {
    await AsyncStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
}
