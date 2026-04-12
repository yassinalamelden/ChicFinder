import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
} from "@/components/ui/card";
import type { ChicFinderResult } from "@/types/api";
import { PRODUCT_CARD, THEME } from "@/lib/constants";

interface ProductCardProps {
  result: ChicFinderResult;
}

const BUTTON_BASE_STYLE =
  "w-full inline-flex items-center justify-center h-10 px-4 py-2 rounded-md font-display tracking-widest text-base transition-colors";

export function ProductCard({ result }: ProductCardProps) {
  const {
    image_id,
    similarity_score,
    brand,
    price_egp,
    product_url,
    store_location,
    availability_egypt,
  } = result;

  const scorePercent = Math.round(similarity_score * 100);

  return (
    <Card className="bg-cf-card border-cf-border hover:-translate-y-1 transition-transform duration-200 overflow-hidden flex flex-col">
      {/* Product image */}
      <div className="relative h-48 bg-zinc-900 overflow-hidden">
        {result.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={result.image_url}
            alt={brand ?? image_id}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <span className="text-6xl opacity-15">{PRODUCT_CARD.IMAGE_PLACEHOLDER_EMOJI}</span>
          </div>
        )}
        {/* Similarity badge */}
        <Badge className="absolute top-3 right-3 bg-cf-accent text-cf-bg font-semibold text-xs">
          {scorePercent}{PRODUCT_CARD.MATCH_SUFFIX}
        </Badge>
        {/* Unavailable ribbon */}
        {!availability_egypt && (
          <div
            className="absolute top-3 left-3 text-white text-xs px-2 py-0.5 rounded"
            style={{ backgroundColor: THEME.COLORS.UNAVAILABLE_BG }}
          >
            {PRODUCT_CARD.NOT_IN_EGYPT}
          </div>
        )}
      </div>

      <CardHeader className="pb-1 pt-4 px-4">
        {brand && (
          <p className="text-xs tracking-widest uppercase text-cf-accent2 font-medium mb-1">
            {brand}
          </p>
        )}
        <p className="text-lg font-display tracking-wide text-cf-text leading-tight">
          {price_egp != null
            ? `${price_egp.toLocaleString("en-EG")} EGP`
            : PRODUCT_CARD.PRICE_NA}
        </p>
      </CardHeader>

      <CardContent className="px-4 pb-2 flex-1">
        {store_location && (
          <p className="text-xs text-cf-muted flex items-center gap-1.5 mt-1">
            <span>📍</span>
            {store_location}
          </p>
        )}
      </CardContent>

      <CardFooter className="px-4 pb-4 pt-2">
        {product_url ? (
          <a
            href={product_url}
            target="_blank"
            rel="noopener noreferrer"
            className={`${BUTTON_BASE_STYLE} bg-cf-accent text-cf-bg hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cf-accent rounded-md`}
          >
            {PRODUCT_CARD.SHOP_NOW_TEXT}
          </a>
        ) : (
          <div className={`${BUTTON_BASE_STYLE} bg-cf-surface text-cf-muted border border-cf-border cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cf-accent rounded-md`} tabIndex={0}>
            {PRODUCT_CARD.UNAVAILABLE_TEXT}
          </div>
        )}
      </CardFooter>
    </Card>
  );
}
