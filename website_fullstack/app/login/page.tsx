"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";
import {
  signInWithPopup,
  GoogleAuthProvider,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
} from "firebase/auth";
import { auth } from "@/lib/firebase";
import { useAuth } from "@/contexts/AuthContext";
import { CanvasRevealEffect } from "@/components/effects/CanvasRevealEffect";

type Step = "email" | "password" | "success";
type Mode = "signin" | "signup";

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
// LoginPage
// ---------------------------------------------------------------------------

export default function LoginPage() {
  const router = useRouter();
  const { user, loading } = useAuth();

  const [step, setStep] = useState<Step>("email");
  const [mode, setMode] = useState<Mode>("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [formLoading, setFormLoading] = useState(false);
  const [reverseCanvas, setReverseCanvas] = useState(false);

  // Redirect if already logged in
  useEffect(() => {
    if (!loading && user && step !== "success") {
      const onboarded = localStorage.getItem("chicfinder_onboarded");
      router.replace(onboarded ? "/" : "/onboarding");
    }
  }, [user, loading, step, router]);

  const handleEmailSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (email) setStep("password");
  };

  const handleGoogleSignIn = async () => {
    setError("");
    setFormLoading(true);
    try {
      const provider = new GoogleAuthProvider();
      await signInWithPopup(auth, provider);
      triggerSuccess();
    } catch (err: unknown) {
      setError(getFriendlyError(err));
    } finally {
      setFormLoading(false);
    }
  };

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setFormLoading(true);
    try {
      if (mode === "signin") {
        await signInWithEmailAndPassword(auth, email, password);
      } else {
        await createUserWithEmailAndPassword(auth, email, password);
      }
      triggerSuccess();
    } catch (err: unknown) {
      setError(getFriendlyError(err));
    } finally {
      setFormLoading(false);
    }
  };

  const triggerSuccess = () => {
    setStep("success");
    setReverseCanvas(true);
    const onboarded = localStorage.getItem("chicfinder_onboarded");
    setTimeout(() => router.replace(onboarded ? "/" : "/onboarding"), 1800);
  };

  const getFriendlyError = (err: unknown): string => {
    const code = (err as { code?: string }).code ?? "";
    if (code === "auth/wrong-password" || code === "auth/invalid-credential")
      return "Incorrect password. Please try again.";
    if (code === "auth/user-not-found") return "No account found with this email.";
    if (code === "auth/email-already-in-use") return "This email is already registered.";
    if (code === "auth/weak-password") return "Password must be at least 6 characters.";
    if (code === "auth/invalid-email") return "Please enter a valid email address.";
    return "Something went wrong. Please try again.";
  };

  return (
    <div className="relative min-h-screen bg-black overflow-hidden">
      {/* Background canvas */}
      <div className="absolute inset-0 z-0">
        {!reverseCanvas && (
          <CanvasRevealEffect
            animationSpeed={3}
            containerClassName="bg-black"
            colors={[[255, 255, 255], [255, 255, 255]]}
            dotSize={6}
            reverse={false}
          />
        )}
        {reverseCanvas && (
          <CanvasRevealEffect
            animationSpeed={4}
            containerClassName="bg-black"
            colors={[[255, 255, 255], [255, 255, 255]]}
            dotSize={6}
            reverse={true}
          />
        )}
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_rgba(0,0,0,0.85)_0%,_transparent_100%)]" />
        <div className="absolute top-0 left-0 right-0 h-1/3 bg-gradient-to-b from-black to-transparent" />
      </div>

      {/* Navbar */}
      <MiniNavbar />

      {/* Content */}
      <div className="relative z-10 flex min-h-screen items-center justify-center px-4">
        <div className="w-full max-w-sm mt-16">
          <AnimatePresence mode="wait">

            {/* Step: Email */}
            {step === "email" && (
              <motion.div
                key="email"
                initial={{ opacity: 0, x: -60 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -60 }}
                transition={{ duration: 0.4, ease: "easeOut" }}
                className="space-y-6 text-center"
              >
                <div className="space-y-1">
                  <h1 className="text-[2.5rem] font-bold leading-tight tracking-tight text-white">
                    Welcome to ChicFinder
                  </h1>
                  <p className="text-lg text-white/50 font-light">
                    Find fashion that fits you
                  </p>
                </div>

                <div className="space-y-4">
                  <button
                    onClick={handleGoogleSignIn}
                    disabled={formLoading}
                    className="w-full flex items-center justify-center gap-3 bg-white/5 hover:bg-white/10 text-white border border-white/10 rounded-full py-3 px-4 transition-colors disabled:opacity-60"
                  >
                    <svg className="w-5 h-5" viewBox="0 0 24 24">
                      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"/>
                      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                    </svg>
                    <span>Continue with Google</span>
                  </button>

                  <div className="flex items-center gap-4">
                    <div className="h-px bg-white/10 flex-1" />
                    <span className="text-white/40 text-sm">or</span>
                    <div className="h-px bg-white/10 flex-1" />
                  </div>

                  <form onSubmit={handleEmailSubmit}>
                    <div className="relative">
                      <input
                        type="email"
                        placeholder="your@email.com"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="w-full bg-white/5 text-white border border-white/10 rounded-full py-3 px-4 focus:outline-none focus:border-white/30 text-center placeholder:text-white/30"
                        required
                      />
                      <button
                        type="submit"
                        className="absolute right-1.5 top-1.5 w-9 h-9 flex items-center justify-center rounded-full bg-white/10 hover:bg-white/20 text-white transition-colors"
                      >
                        →
                      </button>
                    </div>
                  </form>
                </div>

                <p className="text-xs text-white/30 pt-6">
                  By continuing, you agree to ChicFinder&apos;s Terms and Privacy Policy.
                </p>
              </motion.div>
            )}

            {/* Step: Password */}
            {step === "password" && (
              <motion.div
                key="password"
                initial={{ opacity: 0, x: 60 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 60 }}
                transition={{ duration: 0.4, ease: "easeOut" }}
                className="space-y-6 text-center"
              >
                <div className="space-y-1">
                  <h1 className="text-[2.5rem] font-bold leading-tight text-white">
                    {mode === "signin" ? "Welcome back" : "Create account"}
                  </h1>
                  <p className="text-white/50">{email}</p>
                </div>

                <form onSubmit={handlePasswordSubmit} className="space-y-3">
                  <input
                    type="password"
                    placeholder="Password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full bg-white/5 text-white border border-white/10 rounded-full py-3 px-4 focus:outline-none focus:border-white/30 text-center placeholder:text-white/30"
                    required
                    minLength={6}
                  />

                  {error && (
                    <p className="text-red-400 text-sm">{error}</p>
                  )}

                  <div className="flex gap-3 pt-2">
                    <button
                      type="button"
                      onClick={() => { setStep("email"); setError(""); }}
                      className="w-[30%] rounded-full border border-white/10 text-white/70 hover:text-white py-3 transition-colors"
                    >
                      Back
                    </button>
                    <button
                      type="submit"
                      disabled={formLoading}
                      className="flex-1 rounded-full bg-white text-black font-semibold py-3 hover:bg-white/90 transition-colors disabled:opacity-60"
                    >
                      {formLoading ? "..." :mode === "signin" ? "Sign In" : "Sign Up"}
                    </button>
                  </div>
                </form>

                <button
                  onClick={() => { setMode(mode === "signin" ? "signup" : "signin"); setError(""); }}
                  className="text-sm text-white/40 hover:text-white/70 transition-colors"
                >
                  {mode === "signin" ? "New here? Create account" : "Already have an account? Sign in"}
                </button>
              </motion.div>
            )}

            {/* Step: Success */}
            {step === "success" && (
              <motion.div
                key="success"
                initial={{ opacity: 0, y: 40 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -40 }}
                transition={{ duration: 0.4, ease: "easeOut" }}
                className="text-center space-y-6"
              >
                <h1 className="text-[2.5rem] font-bold text-white">You&apos;re in!</h1>
                <motion.div
                  initial={{ scale: 0.7, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ delay: 0.3, duration: 0.5 }}
                  className="mx-auto w-16 h-16 rounded-full bg-white flex items-center justify-center"
                >
                  <svg className="w-8 h-8 text-black" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                </motion.div>
                <p className="text-white/50">Welcome to ChicFinder</p>
              </motion.div>
            )}

          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
