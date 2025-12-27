import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";

interface AppState {
  userId: number | null;
  apiStatus: "checking" | "online" | "offline";
  setUserId: (userId: number | null) => void;
  setApiStatus: (apiStatus: "checking" | "online" | "offline") => void;
}

export const useStore = create<AppState>()(
  devtools(
    persist(
      (set) => ({
        userId: null,
        apiStatus: "checking",
        setUserId: (userId) => set({ userId }),
        setApiStatus: (apiStatus) => set({ apiStatus }),
      }),
      {
        name: "tastekid-storage",
      }
    )
  )
);
