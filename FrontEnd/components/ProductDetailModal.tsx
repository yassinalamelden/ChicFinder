"use client";

import { useEffect, useState } from "react";
import { X, ChevronLeft, ChevronRight, ExternalLink } from "lucide-react";

export interface ModalProduct {
  title?: string;
  brand?: string;
  price_egp?: number;
  image_urls: string[];
  description?: string | null;
  availability?: string;
  product_url?: string;
}

interface ProductDetailModalProps {
  product: ModalProduct | null;
  onClose: () => void;
}

export function ProductDetailModal({ product, onClose }: ProductDetailModalProps) {
  const [activeIndex, setActiveIndex] = useState(0);

  // Reset photo index whenever a new product is opened
  useEffect(() => {
    setActiveIndex(0);
  }, [product]);

  // Keyboard navigation
  useEffect(() => {
    if (!product) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowLeft")
        setActiveIndex((i) => Math.max(0, i - 1));
      if (e.key === "ArrowRight")
        setActiveIndex((i) => Math.min(product.image_urls.length - 1, i + 1));
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [product, onClose]);

  if (!product) return null;

  const images = product.image_urls;
  const inStock = product.availability === "InStock";
  const safeUrl =
    product.product_url?.startsWith("http") ? product.product_url : null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <div
        className="relative bg-zinc-900 rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto flex flex-col md:flex-row shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 z-10 text-white/60 hover:text-white transition-colors"
          aria-label="Close"
        >
          <X className="w-6 h-6" />
        </button>

        {/* ── Left: images ── */}
        <div className="md:w-1/2 flex-shrink-0 flex flex-col">
          {/* Main photo */}
          <div className="relative aspect-square bg-zinc-800 rounded-t-2xl md:rounded-l-2xl md:rounded-tr-none overflow-hidden">
            {images[activeIndex] ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={images[activeIndex]}
                alt={product.title ?? "Product"}
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-6xl opacity-20">
                👗
              </div>
            )}

            {images.length > 1 && (
              <>
                <button
                  onClick={() => setActiveIndex((i) => Math.max(0, i - 1))}
                  disabled={activeIndex === 0}
                  className="absolute left-3 top-1/2 -translate-y-1/2 bg-black/50 hover:bg-black/80 text-white rounded-full p-1.5 disabled:opacity-30 transition-colors"
                  aria-label="Previous image"
                >
                  <ChevronLeft className="w-5 h-5" />
                </button>
                <button
                  onClick={() =>
                    setActiveIndex((i) => Math.min(images.length - 1, i + 1))
                  }
                  disabled={activeIndex === images.length - 1}
                  className="absolute right-3 top-1/2 -translate-y-1/2 bg-black/50 hover:bg-black/80 text-white rounded-full p-1.5 disabled:opacity-30 transition-colors"
                  aria-label="Next image"
                >
                  <ChevronRight className="w-5 h-5" />
                </button>
              </>
            )}
          </div>

          {/* Thumbnail strip */}
          {images.length > 1 && (
            <div className="flex gap-2 p-3 overflow-x-auto bg-zinc-900/80">
              {images.map((url, i) => (
                <button
                  key={i}
                  onClick={() => setActiveIndex(i)}
                  className={`flex-shrink-0 w-14 h-14 rounded-lg overflow-hidden border-2 transition-all ${
                    i === activeIndex
                      ? "border-white"
                      : "border-transparent opacity-50 hover:opacity-100"
                  }`}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={url}
                    alt={`View ${i + 1}`}
                    className="w-full h-full object-cover"
                  />
                </button>
              ))}
            </div>
          )}
        </div>

        {/* ── Right: info ── */}
        <div className="md:w-1/2 p-6 flex flex-col gap-4">
          {product.brand && (
            <p className="text-xs tracking-widest uppercase text-white/50">
              {product.brand}
            </p>
          )}
          {product.title && (
            <h2 className="text-xl font-bold text-white leading-snug">
              {product.title}
            </h2>
          )}
          {product.price_egp != null && (
            <p className="text-2xl font-semibold text-white">
              EGP {product.price_egp.toLocaleString("en-EG")}
            </p>
          )}

          <span
            className={`inline-flex w-fit items-center px-3 py-1 rounded-full text-xs font-medium ${
              inStock
                ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
                : "bg-zinc-700/40 text-zinc-400 border border-zinc-600/30"
            }`}
          >
            {inStock ? "In Stock" : "Out of Stock"}
          </span>

          {product.description && (
            <p className="text-sm text-white/60 leading-relaxed">
              {product.description}
            </p>
          )}

          {safeUrl && (
            <a
              href={safeUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-auto flex items-center justify-center gap-2 w-full py-3 rounded-xl bg-white text-black font-semibold text-sm hover:bg-white/90 transition-colors"
            >
              Shop Now <ExternalLink className="w-4 h-4" />
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
