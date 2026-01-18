import { Link } from "react-router-dom";
import { Layers } from "lucide-react";

import { useNextMovie, useRatingQueue, useRateMovie } from "../lib/hooks";
import { useStore } from "../lib/store";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Separator } from "../components/ui/separator";
import { Skeleton } from "../components/ui/skeleton";
import { EmptyState } from "../components/EmptyState";
import { PosterImage } from "../components/PosterImage";
import { formatDate } from "../lib/utils";

export function RatePage() {
  const userId = useStore((state) => state.userId);

  const { data: nextMovie, isLoading: nextLoading } = useNextMovie(userId);
  const { data: ratingQueue, isLoading: queueLoading } = useRatingQueue(userId);

  const rateMovie = useRateMovie();

  const loading = Boolean(nextLoading || queueLoading);
  const nextPoster = nextMovie ? nextMovie.poster_url ?? nextMovie.backdrop_url : null;
  const yearLabel = nextMovie?.release_date ? formatDate(nextMovie.release_date) : null;

  if (!userId) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center px-6 text-center">
        <h2 className="text-2xl font-semibold tracking-tight">Sign in to start rating</h2>
        <p className="mt-2 max-w-sm text-muted-foreground">
          Rating a few movies helps us tune recommendations to you.
        </p>
        <div className="mt-6">
          <Button asChild>
            <Link to="/login">Sign in</Link>
          </Button>
        </div>
      </div>
    );
  }

  return (
      <div className="space-y-8">
      <div className="space-y-4">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Rate</h1>
          <p className="text-sm text-muted-foreground">A few quick ratings go a long way.</p>
        </div>

        <div>
          {loading && !nextMovie ? (
            <Skeleton className="h-[220px] w-full rounded-2xl" />
          ) : nextMovie ? (
            <Card className="overflow-hidden border-border/50 bg-card/60 backdrop-blur-sm">
              <CardHeader className="pb-4">
                <CardTitle className="text-base">Up next</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 sm:grid-cols-[260px_1fr] sm:items-start">
                  <Link
                    to={`/movie/${nextMovie.id}`}
                    className="group relative overflow-hidden rounded-xl border border-border/50 bg-muted/30"
                    title={nextMovie.title ?? "Movie"}
                  >
                    <div className="aspect-[2/3] w-full max-w-[240px] sm:max-w-[260px]">
                      {nextPoster ? (
                        <PosterImage
                          src={nextPoster}
                          alt={nextMovie.title ?? "Movie"}
                          className="opacity-90 transition-transform duration-500 group-hover:scale-105"
                        />
                      ) : (
                        <div className="flex h-full w-full items-center justify-center text-xs text-muted-foreground">
                          No poster
                        </div>
                      )}
                    </div>
                  </Link>

                  <div className="min-w-0">
                    <div className="space-y-1">
                      <div className="text-lg font-semibold leading-tight text-foreground line-clamp-2">
                        {nextMovie.title ?? "Untitled"}
                      </div>
                      {yearLabel ? (
                        <div className="text-xs text-muted-foreground">{yearLabel}</div>
                      ) : null}
                    </div>

                    <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
                      <div className="flex gap-2">
                        {[5, 4, 3, 2, 1].map((rating) => (
                          <Button
                            key={rating}
                            variant="outline"
                            className="h-10 w-10 rounded-lg"
                            onClick={() =>
                              rateMovie.mutate({ userId, movieId: nextMovie.id, rating, status: "watched" })
                            }
                          >
                            {rating}
                          </Button>
                        ))}
                      </div>

                      <div className="flex gap-2">
                        <Button
                          variant="secondary"
                          className="h-10"
                          onClick={() =>
                            rateMovie.mutate({ userId, movieId: nextMovie.id, rating: null, status: "unwatched" })
                          }
                        >
                          Didn't watch
                        </Button>
                        <Button asChild variant="ghost" className="h-10">
                          <Link to={`/movie/${nextMovie.id}`}>Details</Link>
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ) : (
            <EmptyState title="Nothing queued" description="You're all caught up for now." />
          )}
        </div>
      </div>

      <Separator className="opacity-40" />

      <div className="space-y-4">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Layers className="h-4 w-4" />
          <h2 className="text-sm font-semibold uppercase tracking-widest">Queue</h2>
        </div>

        {loading && !(ratingQueue?.length ?? 0) ? (
          <Skeleton className="h-24 w-full rounded-2xl" />
        ) : ratingQueue?.length ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {ratingQueue.slice(0, 6).map((item) => (
              <div
                key={item.id}
                className="group relative aspect-[16/9] overflow-hidden rounded-2xl border border-border/50 bg-muted/30"
              >
                {item.poster_url || item.backdrop_url ? (
                  <PosterImage
                    src={item.poster_url ?? item.backdrop_url ?? ""}
                    alt={item.title ?? "Movie"}
                    className="opacity-80 transition-transform duration-500 group-hover:scale-105"
                  />
                ) : null}
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent p-4 flex flex-col justify-end">
                  <p className="text-xs font-semibold text-white line-clamp-1">{item.title}</p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState title="Queue is empty" description="We'll add more picks as you rate." />
        )}
      </div>
    </div>
  );
}
