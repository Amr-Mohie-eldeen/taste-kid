import { useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useStore } from "../lib/store";
import { useMovieDetail, useSimilarMovies, useRateMovie, useFeed } from "../lib/hooks";
import { usePosterHydration } from "../lib/usePosterHydration";
import { Button } from "../components/ui/button";
import { Card, CardContent } from "../components/ui/card";
import { Separator } from "../components/ui/separator";
import { Skeleton } from "../components/ui/skeleton";
import { EmptyState } from "../components/EmptyState";
import { MovieCard } from "../components/MovieCard";
import { PosterImage } from "../components/PosterImage";
import { SectionHeader } from "../components/SectionHeader";
import { formatDate } from "../lib/utils";

export function MovieDetail() {
  const { movieId } = useParams();
  const navigate = useNavigate();
  const { userId, posterMap } = useStore();
  
  const id = Number(movieId);

  // Queries
  const { data: detail, isLoading: movieLoading, error: movieError } = useMovieDetail(id);
  const { data: similar, isLoading: similarLoading } = useSimilarMovies(id);
  // Backend caps k at 100; use max allowed to find match score
  const { data: feed } = useFeed(userId, 100);
  
  // Mutations
  const rateMovie = useRateMovie();
  const [rateError, setRateError] = useState<string | null>(null);

  // Poster Hydration
  usePosterHydration(similar?.map((item) => item.id));

  const handleRate = async (rating: number | null, status: string) => {
    if (!userId || !id) {
      if (!userId) {
        setRateError(null);
      } else {
        setRateError("Invalid movie.");
      }
      return;
    }
    setRateError(null);
    try {
      await rateMovie.mutateAsync({ userId, movieId: id, rating, status });
    } catch (error) {
      setRateError(error instanceof Error ? error.message : "Failed to save rating.");
    }
  };

  const meta = useMemo(() => {
    if (!detail) return [] as string[];
    const list: string[] = [];
    if (detail.release_date) list.push(`Release ${formatDate(detail.release_date)}`);
    if (detail.runtime) list.push(`${detail.runtime} min`);
    if (detail.vote_average)
      list.push(`${detail.vote_average.toFixed(1)} / 10 (${detail.vote_count})`);
    if (detail.original_language) list.push(detail.original_language.toUpperCase());
    return list;
  }, [detail]);

  const similarityScore = useMemo(() => {
    const sim = feed?.find((item) => item.id === id)?.similarity ?? null;
    return typeof sim === "number" && !Number.isNaN(sim)
      ? Math.round(Math.min(100, Math.max(0, sim * 100)))
      : null;
  }, [feed, id]);

  if (movieLoading) {
    return (
      <div className="grid gap-8 lg:grid-cols-[1fr_1.2fr]">
        <Skeleton className="aspect-[2/3] w-full rounded-2xl" />
        <div className="space-y-4">
          <Skeleton className="h-10 w-2/3" />
          <Skeleton className="h-4 w-1/2" />
          <Skeleton className="h-24" />
          <Skeleton className="h-12 w-1/3" />
        </div>
      </div>
    );
  }

  if (movieError || !detail) {
    return (
      <div>
        <EmptyState title="Unable to load" description={movieError instanceof Error ? movieError.message : "Movie not found"} />
        <Button className="mt-6" onClick={() => navigate("/")}>Back</Button>
      </div>
    );
  }

  return (
    <div className="space-y-10">
      <div className="flex items-center justify-between">
        <Link className="text-sm text-muted-foreground hover:text-foreground" to="/">
          ← Back to dashboard
        </Link>
      </div>

      <div className="grid gap-8 lg:grid-cols-[1fr_1.2fr]">
        <Card className="overflow-hidden">
          <CardContent className="p-6">
            <div className="relative aspect-[2/3] w-full overflow-hidden rounded-2xl bg-muted">
              {detail.poster_url || detail.backdrop_url ? (
                <PosterImage
                  src={detail.poster_url ?? detail.backdrop_url ?? ""}
                  alt={detail.title ?? "Movie"}
                />
              ) : (
                <div className="flex h-full items-center justify-center bg-gradient-to-br from-slate-200 to-slate-100 text-xs text-muted-foreground">
                  No poster
                </div>
              )}
              {similarityScore !== null && (
                <div className="absolute right-3 top-3 z-10">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full border border-white/20 bg-black/60 text-[11px] font-bold text-white backdrop-blur-md">
                    {similarityScore}%
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        <div className="space-y-5">
          <div>
            <h1 className="text-3xl font-semibold text-foreground">{detail.title}</h1>
            {detail.tagline ? (
              <p className="mt-1 text-sm text-muted-foreground">{detail.tagline}</p>
            ) : null}
          </div>
          <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
            {meta.map((item) => (
              <span key={item}>{item}</span>
            ))}
          </div>
          <p className="text-sm text-muted-foreground">{detail.overview}</p>

          <Separator />
          <SectionHeader title="Rate this movie" />
          <div className="flex flex-wrap gap-2">
            {[5, 4, 3, 2, 1].map((rating) => (
              <Button
                key={rating}
                size="sm"
                variant="outline"
                onClick={() => handleRate(rating, "watched")}
                disabled={rateMovie.isPending}
              >
                {rating}★
              </Button>
            ))}
            <Button 
              size="sm" 
              variant="ghost" 
              onClick={() => handleRate(null, "unwatched")}
              disabled={rateMovie.isPending}
            >
              Mark as unwatched
            </Button>
          </div>
          {!userId && (
            <p className="text-sm text-amber-600">Select a profile first on the dashboard to rate movies.</p>
          )}
          {rateError && <p className="text-sm text-destructive">{rateError}</p>}
          {rateMovie.isSuccess && <p className="text-sm text-primary">Rating saved.</p>}
          {rateMovie.isError && !rateError && <p className="text-sm text-destructive">Failed to save rating.</p>}
        </div>
      </div>

      <div className="space-y-4">
        <SectionHeader title="Similar picks" />
        {similarLoading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3].map((i) => <Skeleton key={i} className="h-48" />)}
          </div>
        ) : similar && similar.length ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {similar.map((item) => (
              <MovieCard
                key={item.id}
                title={item.title}
                releaseDateLabel={item.release_date ? formatDate(item.release_date) : null}
                genres={item.genres}
                imageUrl={posterMap[item.id]}
                to={`/movie/${item.id}`}
                similarity={item.score}
              />
            ))}
          </div>
        ) : (
          <EmptyState title="No similar movies" />
        )}
      </div>
    </div>
  );
}
