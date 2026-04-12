"use client";

import { ArrowLeft, ArrowRight } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Carousel,
  CarouselApi,
  CarouselContent,
  CarouselItem,
} from "@/components/ui/carousel";
import { ProductCardSkeleton } from "@/components/ProductCardSkeleton";
import type { ChicFinderResult } from "@/types/api";

interface ProductGalleryProps {
  results: ChicFinderResult[];
  isLoading?: boolean;
  processingTimeMs?: number;
}

function ResultCard({ result }: { result: ChicFinderResult }) {
  const pct = Math.round(result.similarity_score * 100);

  return (
    <a
      href={result.product_url ?? "#"}
      target="_blank"
      rel="noopener noreferrer"
      className="group rounded-xl block"
    >
      <div className="group relative h-full min-h-[27rem] max-w-full overflow-hidden rounded-xl md:aspect-[5/4] lg:aspect-[4/5]">
        {result.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={result.image_url}
            alt={result.brand ?? "Fashion item"}
            className="absolute h-full w-full object-cover object-center transition-transform duration-300 group-hover:scale-105"
          />
        ) : (
          <div className="absolute inset-0 bg-zinc-900 flex items-center justify-center text-4xl">
            👗
          </div>
        )}

        {/* Gradient overlay */}
        <div className="absolute inset-0 bg-[linear-gradient(transparent_40%,rgba(0,0,0,0.85)_100%)]" />

        {/* Similarity badge */}
        <div className="absolute top-3 right-3 bg-black/60 backdrop-blur-sm border border-white/10 rounded-full px-2 py-0.5 text-xs text-white font-medium">
          {pct}% match
        </div>

        {/* Info */}
        <div className="absolute inset-x-0 bottom-0 flex flex-col items-start p-5 text-white">
          <p className="text-base font-semibold leading-tight">{result.brand ?? "Brand"}</p>
          {result.price_egp != null && (
            <p className="text-sm text-white/70 mt-0.5">EGP {result.price_egp.toLocaleString()}</p>
          )}
          {result.store_location && (
            <p className="text-xs text-white/50 mt-0.5">{result.store_location}</p>
          )}
          <div className="mt-3 flex items-center text-sm font-medium">
            Shop Now
            <ArrowRight className="ml-1.5 w-4 h-4 transition-transform group-hover:translate-x-1" />
          </div>
        </div>
      </div>
    </a>
  );
}

export function ProductGallery({
  results,
  isLoading = false,
  processingTimeMs,
}: ProductGalleryProps) {
  const [carouselApi, setCarouselApi] = useState<CarouselApi>();
  const [canScrollPrev, setCanScrollPrev] = useState(false);
  const [canScrollNext, setCanScrollNext] = useState(false);
  const [currentSlide, setCurrentSlide] = useState(0);

  useEffect(() => {
    if (!carouselApi) return;
    const update = () => {
      setCanScrollPrev(carouselApi.canScrollPrev());
      setCanScrollNext(carouselApi.canScrollNext());
      setCurrentSlide(carouselApi.selectedScrollSnap());
    };
    update();
    carouselApi.on("select", update);
    return () => { carouselApi.off("select", update) };
  }, [carouselApi]);

  if (isLoading) {
    return (
      <section className="py-8">
        <div className="flex gap-5 overflow-hidden px-6">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex-shrink-0 w-[320px]">
              <ProductCardSkeleton />
            </div>
          ))}
        </div>
      </section>
    );
  }

  if (results.length === 0) return null;

  return (
    <section className="py-8">
      {/* Header */}
      <div className="px-6 mb-6 flex items-end justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Similar Items Found</h2>
          {processingTimeMs != null && (
            <p className="text-sm text-white/40 mt-0.5">
              {results.length} results · {processingTimeMs.toFixed(0)} ms
            </p>
          )}
        </div>
        <div className="hidden md:flex gap-2">
          <Button
            size="icon"
            variant="ghost"
            onClick={() => carouselApi?.scrollPrev()}
            disabled={!canScrollPrev}
            className="text-white/60 hover:text-white disabled:opacity-30"
          >
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <Button
            size="icon"
            variant="ghost"
            onClick={() => carouselApi?.scrollNext()}
            disabled={!canScrollNext}
            className="text-white/60 hover:text-white disabled:opacity-30"
          >
            <ArrowRight className="w-5 h-5" />
          </Button>
        </div>
      </div>

      {/* Carousel */}
      <div className="w-full">
        <Carousel
          setApi={setCarouselApi}
          opts={{ breakpoints: { "(max-width: 768px)": { dragFree: true } } }}
        >
          <CarouselContent className="ml-0 pl-6 2xl:ml-[max(1.5rem,calc(50vw-700px))]">
            {results.map((result) => (
              <CarouselItem
                key={result.image_id}
                className="max-w-[300px] pl-[20px] lg:max-w-[340px]"
              >
                <ResultCard result={result} />
              </CarouselItem>
            ))}
          </CarouselContent>
        </Carousel>

        {/* Dot indicators */}
        <div className="mt-5 flex justify-center gap-1.5">
          {results.map((_, i) => (
            <button
              key={i}
              onClick={() => carouselApi?.scrollTo(i)}
              className={`h-1.5 rounded-full transition-all ${
                currentSlide === i ? "w-4 bg-white" : "w-1.5 bg-white/25"
              }`}
              aria-label={`Go to slide ${i + 1}`}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
