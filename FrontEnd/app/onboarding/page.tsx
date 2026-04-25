"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";
import { CanvasRevealEffect } from "@/components/effects/CanvasRevealEffect";
import FeatureCardStack from "@/app/components/onboarding/FeatureCardStack";

const FEATURES = [
  {
    icon: "📷",
    title: "Visual Search",
    description: "Snap or upload any outfit photo — our AI finds matching pieces across every partner store instantly.",
  },
  {
    icon: "✨",
    title: "AI Style Matching",
    description: "FashionCLIP reads colour, silhouette, and texture to surface items that genuinely match your vibe.",
  },
  {
    icon: "🏷️",
    title: "Real EGP Prices",
    description: "Every price is pulled live in Egyptian pounds — no currency surprises, no outdated listings.",
  },
  {
    icon: "🏪",
    title: "Cairo & Beyond",
    description: "Hand-picked partner stores from across Cairo, Alexandria, and international brands shipping to Egypt.",
  },
  {
    icon: "🔖",
    title: "Save Your Looks",
    description: "Bookmark outfits and single pieces to a personal collection you can revisit any time.",
  },
];

// ---------------------------------------------------------------------------
// MiniNavbar
// ---------------------------------------------------------------------------

function MiniNavbar() {
  return (
    <header className="fixed top-6 left-1/2 -translate-x-1/2 z-20 flex items-center gap-6 px-6 py-3 rounded-full border border-white/10 bg-white/5 backdrop-blur-sm">
      <span className="text-sm font-semibold tracking-widest text-white/80 uppercase">
        ChicFinder
      </span>
    </header>
  );
}

// ---------------------------------------------------------------------------
// OnboardingPage
// ---------------------------------------------------------------------------

export default function OnboardingPage() {
  const router = useRouter();
  const [showStartBtn, setShowStartBtn] = useState(false);

  // Show start button after cards fan out
  useEffect(() => {
    const timer = setTimeout(() => setShowStartBtn(true), FEATURES.length * 150 + 600);
    return () => clearTimeout(timer);
  }, []);

  const handleStartExploring = () => {
    localStorage.setItem("chicfinder_onboarded", "true");
    router.push("/home");
  };

  return (
    <div className="relative min-h-screen bg-black overflow-hidden">
      {/* Background canvas - reversed */}
      <div className="absolute inset-0 z-0">
        <CanvasRevealEffect
          animationSpeed={4}
          containerClassName="bg-black"
          colors={[[255, 255, 255], [255, 255, 255]]}
          dotSize={6}
          reverse={true}
        />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_rgba(0,0,0,0.85)_0%,_transparent_100%)]" />
        <div className="absolute top-0 left-0 right-0 h-1/3 bg-gradient-to-b from-black to-transparent" />
      </div>

      {/* Navbar */}
      <MiniNavbar />

      {/* Content */}
      <div className="relative z-10 flex min-h-screen items-center justify-center px-4">
        <div className="w-full max-w-sm mt-16">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="space-y-8 text-center"
          >
            <div>
              <h2 className="text-2xl font-bold text-white">Here&apos;s what you can do</h2>
              <p className="text-white/40 text-sm mt-1">Everything you need to discover fashion</p>
            </div>

            <FeatureCardStack features={FEATURES} />

            <AnimatePresence>
              {showStartBtn && (
                <motion.button
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  onClick={handleStartExploring}
                  className="w-full rounded-full bg-white text-black font-semibold py-3 hover:bg-white/90 transition-colors"
                >
                  Start Exploring →
                </motion.button>
              )}
            </AnimatePresence>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
