import { useEffect, useRef } from "react";
import { hydratePosters } from "./utils";
import { useStore } from "./store";

export function usePosterHydration(ids: number[] | undefined) {
  const { posterMap, setPosterMap } = useStore();
  const lastProcessedIds = useRef<string>("");

  useEffect(() => {
    if (!ids || ids.length === 0) return;
    
    const idsString = [...ids].sort((a, b) => a - b).join(",");
    if (idsString === lastProcessedIds.current) return;
    
    const missing = ids.filter(id => posterMap[id] === undefined);
    if (missing.length > 0) {
      lastProcessedIds.current = idsString;
      hydratePosters(ids, posterMap, setPosterMap);
    }
  }, [ids, posterMap, setPosterMap]);
}
