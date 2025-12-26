import { useEffect } from "react";
import { hydratePosters } from "./utils";
import { useStore } from "./store";

export function usePosterHydration(ids: number[] | undefined) {
  const { posterMap, setPosterMap } = useStore();

  useEffect(() => {
    if (ids && ids.length > 0) {
      hydratePosters(ids, posterMap, setPosterMap);
    }
  }, [ids, posterMap, setPosterMap]);
}
