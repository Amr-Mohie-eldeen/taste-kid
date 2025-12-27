import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";

interface AppState {
  userId: number | null;
  apiStatus: "checking" | "online" | "offline";
  posterMap: Record<number, string | null>;
  setUserId: (userId: number | null) => void;
  setApiStatus: (apiStatus: "checking" | "online" | "offline") => void;
  setPosterMap: (posterMap: Record<number, string | null>) => void;
}

export const useStore = create<AppState>()(
  devtools(
    persist(
      (set) => ({
        userId: null,
        apiStatus: "checking",
        posterMap: {},
        setUserId: (userId) => set({ userId }),
        setApiStatus: (apiStatus) => set({ apiStatus }),
        setPosterMap: (posterMap) => set({ posterMap }),
      }),
      {
        name: "tastekid-storage",
      }
    )
  )
);
