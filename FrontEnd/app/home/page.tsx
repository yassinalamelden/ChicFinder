"use client";

import { useState } from "react";
import { Navbar } from "@/components/Navbar";
import { UploadZone } from "@/components/UploadZone";
import { ProductGallery } from "@/components/blocks/ProductGallery";
import { postRecommend } from "@/lib/api";
import type { ChicFinderResult } from "@/types/api";

type SearchState = "idle" | "loading" | "results" | "error";

export default function HomePage() {
  const [state, setState] = useState<SearchState>("idle");
  const [results, setResults] = useState<ChicFinderResult[]>([]);
  const [processingTimeMs, setProcessingTimeMs] = useState<number>(0);
  const [errorMsg, setErrorMsg] = useState("");

  const handleSearch = async (file: File) => {
    setState("loading");
    setErrorMsg("");
    try {
      const data = await postRecommend(file);
      setResults(data.results);
      setProcessingTimeMs(data.processing_time_ms);
      setState("results");
    } catch (err: unknown) {
      setErrorMsg((err as Error).message ?? "Search failed. Please try again.");
      setState("error");
    }
  };

  return (
    <div className="min-h-screen bg-black text-white flex flex-col">
      <Navbar />

      {/* Hero / Upload section */}
      <main className="flex-1 flex flex-col items-center justify-start pt-28 pb-16 px-4">
        <div className="w-full max-w-2xl text-center space-y-4 mb-10">
          <h1 className="text-4xl sm:text-5xl font-bold leading-tight tracking-tight">
            Find fashion that{" "}
            <span className="text-white/50">fits you</span>
          </h1>
          <p className="text-white/50 text-base sm:text-lg">
            Upload an outfit photo and discover similar items from Egyptian &amp; international stores.
          </p>
        </div>

        <UploadZone onFileSelected={handleSearch} isLoading={state === "loading"} />

        {state === "error" && (
          <p className="mt-6 text-red-400 text-sm text-center">{errorMsg}</p>
        )}
      </main>

      {/* Results */}
      {(state === "results" || state === "loading") && (
        <div className="w-full border-t border-white/10 pb-16">
          <ProductGallery
            results={results}
            isLoading={state === "loading"}
            processingTimeMs={processingTimeMs}
          />
        </div>
      )}
    </div>
  );
}
