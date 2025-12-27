import * as React from "react";
import { Link } from "react-router-dom";
import { Badge } from "./ui/badge";
import { Card, CardContent } from "./ui/card";
import { cn } from "../lib/utils";
import { PosterImage } from "./PosterImage";

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
  subtitle,
  releaseDateLabel,
  genres,
  meta = [],
  description,
  imageUrl,
  actions,
  to,
  layout = "default",
  imageClassName,
  cardClassName,
  similarity,
}: MovieCardProps) {
  const genreList = genres?.split(",").map((genre) => genre.trim()).filter(Boolean) ?? [];
  const visibleGenres = genreList.slice(0, 2);
  const remainingGenres = Math.max(0, genreList.length - visibleGenres.length);
  const similarityValue = similarity ?? null;
  const similarityPercent = similarityValue === null
    ? null
    : Math.round(Math.min(100, similarityValue <= 1 ? similarityValue * 100 : similarityValue));

  const content = (
    <CardContent
      className={cn(
        "flex flex-grow flex-col gap-4 p-4",
        layout === "row" ? "sm:flex-row" : ""
      )}
    >
      <div
        className={cn(
          "relative w-full overflow-hidden rounded-xl bg-muted shadow-inner",
          layout === "row" ? "aspect-[2/3] sm:w-32 flex-shrink-0" : "aspect-[16/9]",
          imageClassName
        )}
      >
        {imageUrl ? (
          <PosterImage
            src={imageUrl}
            alt={title ?? "Movie"}
            className="transition-transform duration-700 ease-out group-hover:scale-110"
          />
        ) : (
          <div className="flex h-full items-center justify-center bg-gradient-to-br from-muted to-accent text-xs font-medium text-muted-foreground uppercase tracking-widest">
            No Poster
          </div>
        )}
        {similarityPercent !== null && (
          <div className="absolute right-2 top-2 z-10">
            <div className="flex h-9 w-9 items-center justify-center rounded-full border border-white/20 bg-black/60 text-[10px] font-bold text-white backdrop-blur-md">
              {similarityPercent}%
            </div>
          </div>
        )}
      </div>
      <div className="flex flex-grow flex-col space-y-2.5">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1">
            <h4 className="line-clamp-1 text-base font-bold tracking-tight text-foreground group-hover:text-primary transition-colors">
              {title ?? "Untitled"}
            </h4>
            <div className="flex items-center gap-2">
              {releaseDateLabel ? (
                <span className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground/80">
                  {releaseDateLabel}
                </span>
              ) : null}
              {releaseDateLabel && visibleGenres.length > 0 && (
                <span className="h-1 w-1 rounded-full bg-border" />
              )}
              {visibleGenres.length ? (
                <p className="line-clamp-1 text-[11px] font-medium text-muted-foreground/80 uppercase tracking-wider">
                  {visibleGenres.join(" • ")}
                </p>
              ) : null}
            </div>
          </div>
        </div>
        
        {subtitle && (
          <p className="line-clamp-1 text-xs italic text-muted-foreground">{subtitle}</p>
        )}

        {description ? (
          <p className="line-clamp-2 text-[13px] leading-relaxed text-muted-foreground/90">
            {description}
          </p>
        ) : null}

        {meta.length ? (
          <div className="flex flex-wrap gap-x-3 gap-y-1 text-[11px] font-medium text-muted-foreground">
            {meta.map((item) => (
              <span key={item} className="flex items-center gap-1.5">
                <span className="h-1 w-1 rounded-full bg-primary/40" />
                {item}
              </span>
            ))}
          </div>
        ) : null}
        
        {actions ? <div className="mt-auto flex flex-wrap gap-2 pt-2">{actions}</div> : null}
      </div>
    </CardContent>
  );

  const card = (
    <Card
      className={cn(
        "group h-full overflow-hidden border-border/40 bg-card/50 transition-all duration-300 backdrop-blur-sm",
        to && "hover:-translate-y-1.5 hover:border-primary/20 hover:shadow-[0_20px_40px_-15px_rgba(0,0,0,0.1)] hover:bg-card",
        cardClassName
      )}
    >
      {content}
    </Card>
  );

  if (!to) return card;

  return (
    <Link className="block h-full" to={to}>
      {card}
    </Link>
  );
}