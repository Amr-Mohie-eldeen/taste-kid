import { useQuery, useMutation, useQueryClient, keepPreviousData } from "@tanstack/react-query";
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
  return useQuery({
    queryKey: ["feed", userId, limit],
    queryFn: () => api.getFeed(userId!, limit),
    enabled: !!userId,
    placeholderData: keepPreviousData,
  });
}

export function useRecommendations(userId: number | null, limit: number) {
  return useQuery({
    queryKey: ["recommendations", userId, limit],
    queryFn: () => api.getRecommendations(userId!, limit),
    enabled: !!userId,
    placeholderData: keepPreviousData,
  });
}

// Ratings & Queue Hooks
export function useRatings(userId: number | null, limit?: number) {
  return useQuery({
    queryKey: ["ratings", userId, limit],
    queryFn: () => api.getRatings(userId!, limit),
    enabled: !!userId,
  });
}

export function useRatingQueue(userId: number | null) {
  return useQuery({
    queryKey: ["ratingQueue", userId],
    queryFn: () => api.getRatingQueue(userId!),
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
    onSuccess: (_, { userId }) => {
      queryClient.invalidateQueries({ queryKey: ["ratingQueue", userId] });
      queryClient.invalidateQueries({ queryKey: ["nextMovie", userId] });
      queryClient.invalidateQueries({ queryKey: ["ratings", userId] });
      queryClient.invalidateQueries({ queryKey: ["profileStats", userId] });
      queryClient.invalidateQueries({ queryKey: ["userSummary", userId] });
      queryClient.invalidateQueries({ queryKey: ["feed", userId] });
      queryClient.invalidateQueries({ queryKey: ["recommendations", userId] });
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



export function useSimilarMovies(movieId: number) {

  return useQuery({

    queryKey: ["similarMovies", movieId],

    queryFn: () => api.getSimilar(movieId),

    enabled: !!movieId && !Number.isNaN(movieId),

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

      return { detail, similar };

    },

    enabled: enabled && !!query.trim(),

    retry: false,

  });

}
