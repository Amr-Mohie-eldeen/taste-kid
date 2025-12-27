import { useQuery, useMutation, useQueryClient, useInfiniteQuery } from "@tanstack/react-query";
import { api } from "./api";
import { useStore } from "./store";

// User & Profile Hooks
export function useUserSummary(userId: number | null) {
  return useQuery({
    queryKey: ["userSummary", userId],
    queryFn: () => api.getUserSummary(userId!),
    enabled: !!userId,
  });
}

export function useProfileStats(userId: number | null) {
  return useQuery({
    queryKey: ["profileStats", userId],
    queryFn: () => api.getProfileStats(userId!),
    enabled: !!userId,
  });
}

export function useCreateUser() {
  const queryClient = useQueryClient();
  const { setUserId } = useStore();
  
  return useMutation({
    mutationFn: (name: string | null) => api.createUser(name),
    onSuccess: (data) => {
      setUserId(data.id);
      queryClient.invalidateQueries({ queryKey: ["userSummary", data.id] });
    },
  });
}

// Feed & Recommendations Hooks
export function useFeed(userId: number | null, limit: number) {
  return useInfiniteQuery({
    queryKey: ["feed", userId, limit],
    queryFn: ({ pageParam }) => api.getFeed(userId!, limit, pageParam ?? null),
    getNextPageParam: (lastPage) => lastPage.meta.has_more ? lastPage.meta.next_cursor ?? undefined : undefined,
    enabled: !!userId,
    initialPageParam: null,
  });
}

// Discovery removed from UI; recommendations hook unused

// Ratings & Queue Hooks
export function useRatings(userId: number | null, limit = 20) {
  return useInfiniteQuery({
    queryKey: ["ratings", userId, limit],
    queryFn: ({ pageParam }) => api.getRatings(userId!, limit, pageParam ?? null),
    getNextPageParam: (lastPage) => lastPage.meta.has_more ? lastPage.meta.next_cursor ?? undefined : undefined,
    enabled: !!userId,
    initialPageParam: null,
  });
}

export function useRatingQueue(userId: number | null, limit = 20) {
  return useQuery({
    queryKey: ["ratingQueue", userId, limit],
    queryFn: async () => {
      const page = await api.getRatingQueue(userId!, limit, null);
      return page.items;
    },
    enabled: !!userId,
  });
}

export function useNextMovie(userId: number | null) {
  return useQuery({
    queryKey: ["nextMovie", userId],
    queryFn: () => api.getNextMovie(userId!).catch(() => null),
    enabled: !!userId,
  });
}

export function useRateMovie() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ userId, movieId, rating, status }: { userId: number; movieId: number; rating: number | null; status: string }) =>
      api.rateMovie(userId, movieId, rating, status),
    onSuccess: (_, { userId, movieId }) => {
      queryClient.invalidateQueries({ queryKey: ["ratingQueue", userId] });
      queryClient.invalidateQueries({ queryKey: ["nextMovie", userId] });
      queryClient.invalidateQueries({ queryKey: ["ratings", userId] });
      queryClient.invalidateQueries({ queryKey: ["profileStats", userId] });
      queryClient.invalidateQueries({ queryKey: ["userSummary", userId] });
      queryClient.invalidateQueries({ queryKey: ["feed", userId] });
      queryClient.invalidateQueries({ queryKey: ["userMovieMatch", userId, movieId] });
    },
  });
}

// Movie Detail Hooks

export function useMovieDetail(movieId: number) {

  return useQuery({

    queryKey: ["movie", movieId],

    queryFn: () => api.getMovieDetail(movieId),

    enabled: !!movieId && !Number.isNaN(movieId),

  });

}



export function useSimilarMovies(movieId: number, limit = 10) {
  return useQuery({
    queryKey: ["similarMovies", movieId, limit],
    queryFn: async () => {
      const page = await api.getSimilar(movieId, limit, null);
      return page.items;
    },
    enabled: !!movieId && !Number.isNaN(movieId),
  });
}

export function useUserMovieMatch(userId: number | null, movieId: number | null) {
  return useQuery({
    queryKey: ["userMovieMatch", userId, movieId],
    queryFn: () => api.getUserMovieMatch(userId!, movieId!),
    enabled: !!userId && !!movieId && !Number.isNaN(movieId),
  });
}



export function useMovieSearch(query: string, enabled: boolean) {

  return useQuery({

    queryKey: ['search', query],

    queryFn: async () => {

      const lookup = await api.lookupMovie(query);

      const [detail, similar] = await Promise.all([
        api.getMovieDetail(lookup.id),
        api.getSimilar(lookup.id),
      ]);

      return { detail, similar: similar.items };

    },

    enabled: enabled && !!query.trim(),

    retry: false,

  });

}
