import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";

interface AppState {
  userId: number | null;
  token: string | null;
  apiStatus: "checking" | "online" | "offline";
  setUserId: (userId: number | null) => void;
  setToken: (token: string | null) => void;
  setApiStatus: (apiStatus: "checking" | "online" | "offline") => void;
  resetSession: () => void;
}

export const useStore = create<AppState>()(
  devtools(
    persist(
      (set) => ({
        userId: null,
        token: null,
        apiStatus: "checking",
        setUserId: (userId) => set({ userId }),
        setToken: (token) => set({ token }),
        setApiStatus: (apiStatus) => set({ apiStatus }),
        resetSession: () => set({ userId: null, token: null }),
      }),
      {
        name: "tastekid-storage",
      }
    )
  )
);
