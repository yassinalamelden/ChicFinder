"use client";

import { useEffect, useState } from "react";
import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { Navbar } from "@/components/Navbar";
import { getStores } from "@/lib/api";
import type { Store } from "@/types/api";
import { Skeleton } from "@/components/ui/skeleton";

function StoreCardSkeleton() {
  return (
    <div className="rounded-2xl border border-white/10 overflow-hidden">
      <Skeleton className="h-48 w-full bg-white/5" />
      <div className="p-5 space-y-2">
        <Skeleton className="h-5 w-32 bg-white/5" />
        <Skeleton className="h-4 w-48 bg-white/5" />
        <Skeleton className="h-4 w-24 bg-white/5" />
      </div>
    </div>
  );
}

function StoreCard({ store }: { store: Store }) {
  return (
    <Link href={`/stores/${store.id}`} className="group block">
      <div className="rounded-2xl border border-white/10 overflow-hidden hover:border-white/25 transition-colors">
        {/* Image */}
        <div className="relative h-48 bg-zinc-900 overflow-hidden">
          {store.logo_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={store.logo_url}
              alt={store.name}
              className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-4xl">🏪</div>
          )}
          <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
        </div>

        {/* Info */}
        <div className="p-5 space-y-1">
          <p className="font-semibold text-white">{store.name}</p>
          <p className="text-sm text-white/50 line-clamp-2">{store.description}</p>
          {store.location && (
            <p className="text-xs text-white/30 flex items-center gap-1">
              <span>📍</span>{store.location}
            </p>
          )}
          <div className="pt-2 flex items-center text-sm text-white/60 group-hover:text-white transition-colors">
            Browse Store
            <ArrowRight className="ml-1.5 w-4 h-4 transition-transform group-hover:translate-x-1" />
          </div>
        </div>
      </div>
    </Link>
  );
}

export default function StoresPage() {
  const [stores, setStores] = useState<Store[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getStores()
      .then(setStores)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-black text-white flex flex-col">
      <Navbar />

      <main className="flex-1 pt-24 pb-16 px-6 max-w-7xl mx-auto w-full">
        <div className="mb-10">
          <h1 className="text-3xl sm:text-4xl font-bold">Our Partner Stores</h1>
          <p className="text-white/50 mt-2 text-sm">
            Explore all stores that collaborate with ChicFinder.
          </p>
        </div>

        {error && <p className="text-red-400 text-sm mb-6">{error}</p>}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
          {loading
            ? Array.from({ length: 8 }).map((_, i) => <StoreCardSkeleton key={i} />)
            : stores.map((store) => <StoreCard key={store.id} store={store} />)}
        </div>

        {!loading && stores.length === 0 && !error && (
          <p className="text-white/40 text-center mt-16">No stores found.</p>
        )}
      </main>
    </div>
  );
}
