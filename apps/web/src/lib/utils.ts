import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { api } from "./api";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const formatDate = (value?: string | null) => {
  if (!value) return "-";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString();
};

export const hydratePosters = async (
  ids: number[],
  posters: Record<number, string | null>,
  setter: (posters: Record<number, string | null>) => void
) => {
  const missing = ids.filter((id) => posters[id] === undefined);
  if (missing.length === 0) {
    return;
  }

  const results = await Promise.all(
    missing.map((id) => api.getMovieDetail(id).catch(() => null))
  );

  const newPosters = { ...posters };
  results.forEach((detail, index) => {
    const id = missing[index];
    newPosters[id] = detail?.poster_url ?? detail?.backdrop_url ?? null;
  });

  setter(newPosters);
};





