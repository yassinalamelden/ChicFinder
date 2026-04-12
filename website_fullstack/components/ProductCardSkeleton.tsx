import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";

export function ProductCardSkeleton() {
  return (
    <Card className="bg-cf-card border-cf-border overflow-hidden flex flex-col">
      <Skeleton className="h-48 w-full rounded-none bg-cf-surface" />
      <CardHeader className="pb-1 pt-4 px-4">
        <Skeleton className="h-3 w-20 mb-2 bg-cf-border" />
        <Skeleton className="h-6 w-32 bg-cf-border" />
      </CardHeader>
      <CardContent className="px-4 pb-2 flex-1">
        <Skeleton className="h-3 w-40 mt-1 bg-cf-border" />
      </CardContent>
      <CardFooter className="px-4 pb-4 pt-2">
        <Skeleton className="h-10 w-full bg-cf-border" />
      </CardFooter>
    </Card>
  );
}
