import * as React from "react";
import { Link } from "react-router-dom";
import { Card, CardContent } from "./ui/card";
import { cn } from "../lib/utils";
import { PosterImage } from "./PosterImage";
import { Plus } from "lucide-react";
import { Button } from "./ui/button";

type MovieCardProps = {
  title: string | null;
  subtitle?: string | null;
  releaseDateLabel?: string | null;
  genres?: string | null;
  meta?: string[];
  description?: string | null;
  imageUrl?: string | null;
  actions?: React.ReactNode;
  to?: string;
  layout?: "default" | "row";
  imageClassName?: string;
  cardClassName?: string;
  similarity?: number | null;
};

export function MovieCard({
  title,
  releaseDateLabel,
  imageUrl,
  actions,
  to,
  cardClassName,
  similarity,
}: MovieCardProps) {
  const year = releaseDateLabel ? releaseDateLabel.split(",").pop()?.trim() : "";

  const similarityValue = similarity ?? null;
  const similarityPercent = similarityValue === null
    ? null
    : Math.round(Math.min(100, similarityValue <= 1 ? similarityValue * 100 : similarityValue));

  const content = (
    <CardContent className="p-0 relative group h-full">
      <div className="relative aspect-[2/3] w-full overflow-hidden rounded-md bg-muted">
        {imageUrl ? (
          <PosterImage
            src={imageUrl}
            alt={title ?? "Movie"}
            className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full items-center justify-center bg-zinc-900 text-xs font-medium text-zinc-500 uppercase tracking-widest">
            No Poster
          </div>
        )}

        <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-center justify-center backdrop-blur-[2px]">
           <div className="transform scale-90 group-hover:scale-100 transition-transform duration-300">
               {actions ? actions : (
                <Button size="sm" variant="secondary" className="rounded-full h-12 w-12 bg-white/20 hover:bg-white/40 border-0 backdrop-blur-md text-white">
                 <Plus className="h-6 w-6" />
               </Button>
             )}
           </div>
        </div>

        {similarityPercent !== null && (
          <div className="absolute top-2 right-2 z-10">
            <div className="bg-green-500/90 text-white text-[10px] font-bold px-1.5 py-0.5 rounded shadow-sm backdrop-blur-sm">
              {similarityPercent}% Match
            </div>
          </div>
        )}
      </div>

      <div className="mt-2 space-y-0.5 px-1">
        <h4 className="text-sm font-semibold leading-tight text-foreground truncate group-hover:text-primary transition-colors">
          {title ?? "Untitled"}
        </h4>
        <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
           <span>{year}</span>
        </div>
      </div>
    </CardContent>
  );

  const card = (
    <Card
      className={cn(
        "border-0 shadow-none bg-transparent transition-all duration-300",
        cardClassName
      )}
    >
      {content}
    </Card>
  );

  if (!to) return card;

  return (
    <Link className="block h-full group" to={to}>
      {card}
    </Link>
  );
}