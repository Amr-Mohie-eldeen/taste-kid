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
  const visibleGenres = genreList.slice(0, 3);
  const remainingGenres = Math.max(0, genreList.length - visibleGenres.length);
  const similarityValue = similarity ?? null;
  const similarityPercent = similarityValue === null
    ? null
    : Math.round(Math.min(100, similarityValue <= 1 ? similarityValue * 100 : similarityValue));

  const content = (
    <CardContent
      className={cn(
        "flex h-full gap-4 p-5",
        layout === "row" ? "flex-col sm:flex-row" : "flex-col"
      )}
    >
      <div
        className={cn(
          "w-full overflow-hidden rounded-lg bg-muted",
          layout === "row" ? "aspect-[2/3] sm:w-40 sm:shrink-0" : "h-56",
          imageClassName
        )}
      >
        {imageUrl ? (
          <PosterImage
            src={imageUrl}
            alt={title ?? "Movie"}
            className="transition-transform duration-500 ease-out group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full items-center justify-center bg-gradient-to-br from-slate-200 to-slate-100 text-xs text-muted-foreground">
            No poster
          </div>
        )}
      </div>
      <div className="flex h-full flex-col space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h4 className="line-clamp-2 text-lg font-semibold text-foreground">
              {title ?? "Untitled"}
            </h4>
            {releaseDateLabel ? (
              <span className="mt-1 inline-flex rounded-full border border-border bg-white/80 px-2 py-0.5 text-xs text-muted-foreground">
                {releaseDateLabel}
              </span>
            ) : null}
            {subtitle ? <p className="text-sm text-muted-foreground">{subtitle}</p> : null}
          </div>
          {similarityPercent !== null ? (
            <div className="flex h-12 w-12 items-center justify-center rounded-full border border-emerald-200 bg-emerald-50 text-xs font-semibold text-emerald-700">
              {similarityPercent}%
            </div>
          ) : null}
        </div>
        {visibleGenres.length ? (
          <div className="flex flex-wrap gap-2">
            {visibleGenres.map((genre) => (
              <Badge key={genre} variant="secondary">
                {genre}
              </Badge>
            ))}
            {remainingGenres > 0 ? (
              <Badge variant="outline">+{remainingGenres}</Badge>
            ) : null}
          </div>
        ) : null}
        {meta.length ? (
          <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
            {meta.map((item) => (
              <span key={item}>{item}</span>
            ))}
          </div>
        ) : null}
        {description ? (
          <p className="line-clamp-3 text-sm text-muted-foreground">{description}</p>
        ) : null}
        {actions ? <div className="mt-auto flex flex-wrap gap-2">{actions}</div> : null}
      </div>
    </CardContent>
  );

  const card = (
    <Card
      className={cn(
        to
          ? "group overflow-hidden border-border/60 transition hover:-translate-y-1 hover:shadow-glow"
          : "overflow-hidden border-border/60",
        layout === "default" ? "h-full" : "",
        cardClassName
      )}
    >
      {content}
    </Card>
  );

  if (!to) return card;

  return (
    <Link className="block" to={to}>
      {card}
    </Link>
  );
}
