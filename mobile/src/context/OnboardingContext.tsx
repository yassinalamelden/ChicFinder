/**
 * Whether the walkthrough has been seen, held in one place.
 *
 * The first version read the flag straight into the root layout's own state.
 * Finishing the walkthrough wrote to storage and navigated, but nothing told
 * the layout its copy was stale, so the redirect fired again the moment the
 * tabs mounted and bounced the user back. Two owners of one fact.
 *
 * There is now a single owner. `complete()` flips the value in memory FIRST and
 * persists afterwards, so the navigation that follows can never race the write.
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

import { hasOnboarded, markOnboarded, resetOnboarding } from "../lib/onboarding";

interface OnboardingValue {
  /** null while the flag is still being read. Do not route on null. */
  onboarded: boolean | null;
  complete: () => Promise<void>;
  reset: () => Promise<void>;
}

const OnboardingContext = createContext<OnboardingValue | null>(null);

export function OnboardingProvider({ children }: { children: ReactNode }) {
  const [onboarded, setOnboarded] = useState<boolean | null>(null);

  useEffect(() => {
    hasOnboarded().then(setOnboarded);
  }, []);

  const complete = useCallback(async () => {
    // In memory before storage. A failed write costs one extra walkthrough on
    // the next launch; the reverse order costs a redirect loop right now.
    setOnboarded(true);
    await markOnboarded();
  }, []);

  const reset = useCallback(async () => {
    setOnboarded(false);
    await resetOnboarding();
  }, []);

  const value = useMemo<OnboardingValue>(
    () => ({ onboarded, complete, reset }),
    [onboarded, complete, reset]
  );

  return (
    <OnboardingContext.Provider value={value}>{children}</OnboardingContext.Provider>
  );
}

export function useOnboarding(): OnboardingValue {
  const ctx = useContext(OnboardingContext);
  if (!ctx) {
    // Treating "no provider" as already onboarded keeps any screen rendered
    // outside the tree usable rather than trapping it behind a walkthrough.
    return { onboarded: true, complete: async () => {}, reset: async () => {} };
  }
  return ctx;
}
