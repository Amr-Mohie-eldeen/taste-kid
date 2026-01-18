import { useStore } from "../lib/store";
import { useRatings } from "../lib/hooks";
import { MovieCard } from "../components/MovieCard";
import { Loader2, History } from "lucide-react";
import { Button } from "../components/ui/button";
import { Fragment } from "react";
import { Link } from "react-router-dom";

export function HistoryPage() {
  const userId = useStore((state) => state.userId);
  const { data, fetchNextPage, hasNextPage, isFetchingNextPage, isLoading } = useRatings(userId);

  if (!userId) {
    return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] text-center p-6">
            <div className="w-16 h-16 bg-secondary/50 rounded-full flex items-center justify-center mb-6">
                 <History className="w-8 h-8 text-muted-foreground" />
            </div>
            <h2 className="text-2xl font-bold mb-2">Sign in to view history</h2>
            <p className="text-muted-foreground max-w-sm mb-6">
                Track the movies you've watched and rated to get better recommendations.
            </p>
            <Button asChild>
                <Link to="/login">Sign In</Link>
            </Button>
        </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="p-6 md:p-12 max-w-7xl mx-auto min-h-full">
      <div className="flex items-center gap-3 mb-8">
        <div className="p-2 bg-primary/10 rounded-lg">
             <History className="w-6 h-6 text-primary" />
        </div>
        <h1 className="text-3xl font-bold tracking-tight">Watch History</h1>
      </div>

      {!data?.pages?.[0]?.items?.length ? (
        <div className="text-center py-24 bg-secondary/20 rounded-3xl border border-dashed border-zinc-800">
           <p className="text-zinc-500 text-lg">You haven't rated any movies yet.</p>
           <Button variant="ghost" className="mt-2 text-primary hover:text-primary" asChild>
             <Link to="/">Start Exploring</Link>
           </Button>
        </div>
      ) : (
        <div className="space-y-8">
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-x-4 gap-y-8">
            {data.pages.map((page, i) => (
              <Fragment key={i}>
                {page.items.map((item) => (
                    <MovieCard
                     key={item.id}
                     title={item.title}
                     releaseDateLabel={item.updated_at}
                     imageUrl={item.poster_url}
                     to={`/movie/${item.id}`}
                   />
                ))}
              </Fragment>
            ))}
          </div>

          {hasNextPage && (
            <div className="flex justify-center pt-8">
              <Button
                variant="outline"
                onClick={() => fetchNextPage()}
                disabled={isFetchingNextPage}
                className="w-full max-w-xs"
              >
                {isFetchingNextPage ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Loading...
                  </>
                ) : (
                  "Load More"
                )}
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
