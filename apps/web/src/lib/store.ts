import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";

interface AppState {
  userId: number | null;
  userProfile: { name?: string; email?: string; preferred_username?: string } | null;
  token: string | null;
  apiStatus: "checking" | "online" | "offline";
  setUserId: (userId: number | null) => void;
  setUserProfile: (profile: AppState["userProfile"]) => void;
  setToken: (token: string | null) => void;
  setApiStatus: (apiStatus: "checking" | "online" | "offline") => void;
  resetSession: () => void;
}

export const useStore = create<AppState>()(
  devtools(
    persist(
      (set) => ({
        userId: null,
        userProfile: null,
        token: null,
        apiStatus: "checking",
        setUserId: (userId) => set({ userId }),
        setUserProfile: (userProfile) => set({ userProfile }),
        setToken: (token) => set({ token }),
        setApiStatus: (apiStatus) => set({ apiStatus }),
        resetSession: () => set({ userId: null, userProfile: null, token: null }),
      }),
      {
        name: "tastekid-storage",
        partialize: (state) => ({ apiStatus: state.apiStatus }),
      }
    )
  )
);
