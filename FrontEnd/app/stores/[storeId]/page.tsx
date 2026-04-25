"use client";

import { useEffect, useState, useMemo } from "react";
import { useParams } from "next/navigation";
import { ExternalLink } from "lucide-react";
import Link from "next/link";
import { Navbar } from "@/components/Navbar";
import { ProductCard } from "@/components/ProductCard";
import { ProductCardSkeleton } from "@/components/ProductCardSkeleton";
import { getStoreDetail } from "@/lib/api";
import type { Store, StoreItem } from "@/types/api";
import type { ChicFinderResult } from "@/types/api";

const CATEGORIES = ["All", "tops", "bottoms", "shoes"];

function storeItemToResult(item: StoreItem): ChicFinderResult {
  return {
    image_id: item.id,
    similarity_score: 1,
    brand: item.brand,
    price_egp: item.price_egp,
    product_url: item.product_url,
    store_location: item.store_location,
    image_url: item.image_url,
    availability_egypt: true,
  };
}

export default function StoreDetailPage() {
  const { storeId } = useParams<{ storeId: string }>();

  const [store, setStore] = useState<Store | null>(null);
  const [items, setItems] = useState<StoreItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeCategory, setActiveCategory] = useState("All");
  const [search, setSearch] = useState("");

  useEffect(() => {
    if (!storeId) return;
    getStoreDetail(storeId)
      .then((data) => {
        setStore(data.store);
        setItems(data.items);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [storeId]);

  const filtered = useMemo(() => {
    let list = items;
    if (activeCategory !== "All") {
      list = list.filter((i) => i.category === activeCategory);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(
        (i) =>
          i.name.toLowerCase().includes(q) ||
          i.type.toLowerCase().includes(q) ||
          i.color.toLowerCase().includes(q)
      );
    }
    return list;
  }, [items, activeCategory, search]);

  return (
    <div className="min-h-screen bg-black text-white flex flex-col">
      <Navbar />

      <main className="flex-1 pt-24 pb-16 px-6 max-w-7xl mx-auto w-full">
        {/* Back link */}
        <Link href="/stores" className="text-sm text-white/40 hover:text-white transition-colors mb-6 inline-block">
          ← All Stores
        </Link>

        {error && <p className="text-red-400 text-sm mb-6">{error}</p>}

        {/* Store header */}
        {store && (
          <div className="flex items-start gap-5 mb-10">
            {store.logo_url && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={store.logo_url}
                alt={store.name}
                className="w-20 h-20 rounded-2xl object-cover border border-white/10 flex-shrink-0"
              />
            )}
            <div className="flex-1 min-w-0">
              <h1 className="text-3xl font-bold">{store.name}</h1>
              <p className="text-white/50 text-sm mt-1 max-w-lg">{store.description}</p>
              <div className="flex items-center gap-4 mt-3 flex-wrap">
                {store.location && (
                  <span className="text-xs text-white/30">📍 {store.location}</span>
                )}
                {store.website_url && (
                  <a
                    href={store.website_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-xs text-white/50 hover:text-white transition-colors"
                  >
                    Visit Website <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-3 mb-8">
          {/* Category pills */}
          <div className="flex gap-2 flex-wrap">
            {CATEGORIES.map((cat) => (
              <button
                key={cat}
                onClick={() => setActiveCategory(cat)}
                className={`px-4 py-1.5 rounded-full text-sm border transition-colors ${
                  activeCategory === cat
                    ? "border-white bg-white text-black font-medium"
                    : "border-white/15 text-white/50 hover:border-white/40 hover:text-white"
                }`}
              >
                {cat.charAt(0).toUpperCase() + cat.slice(1)}
              </button>
            ))}
          </div>

          {/* Search */}
          <input
            type="text"
            placeholder="Search items..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="sm:ml-auto bg-white/5 border border-white/10 rounded-full px-4 py-1.5 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-white/30 w-full sm:w-56"
          />
        </div>

        {/* Items grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
          {loading
            ? Array.from({ length: 10 }).map((_, i) => <ProductCardSkeleton key={i} />)
            : filtered.map((item) => (
                <ProductCard key={item.id} result={storeItemToResult(item)} />
              ))}
        </div>

        {!loading && filtered.length === 0 && !error && (
          <p className="text-white/40 text-center mt-16">No items match your filters.</p>
        )}
      </main>
    </div>
  );
}
