import { useEffect } from "react";
import { BrowserRouter, Route, Routes, Navigate } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { api } from "./lib/api";
import { DashboardLayout } from "./components/layouts/DashboardLayout";
import { HomePage } from "./pages/HomePage";
import { Login } from "./pages/Login";
import { MovieDetail } from "./pages/MovieDetail";
import { Signup } from "./pages/Signup";
import { SearchPage } from "./pages/SearchPage";
import { RatePage } from "./pages/RatePage";
import { HistoryPage } from "./pages/HistoryPage";
import { ProfilePage } from "./pages/ProfilePage";
import { useStore } from "./lib/store";
import { queryClient } from "./lib/queryClient";

export default function App() {
  const { setApiStatus, setUserId, setToken, userId } = useStore();

  useEffect(() => {
    api
      .health()
      .then(() => setApiStatus("online"))
      .catch(() => setApiStatus("offline"));
  }, [setApiStatus]);

  useEffect(() => {
    let cancelled = false;

    void (async () => {
      const storeToken = useStore.getState().token;
      const accessToken = storeToken ?? (await (await import("./lib/oidc")).getAccessToken());

      if (cancelled) {
        return;
      }

      if (!accessToken) {
        const store = useStore.getState();
        if (store.userId || store.token || store.userProfile) {
          store.resetSession();
        }
        return;
      }

      setToken(accessToken);

      try {
        const { oidc } = await import("./lib/oidc");
        const oidcState = await oidc.getOidc();
        if (oidcState.isUserLoggedIn) {
          const profile = oidcState.getDecodedIdToken();
          useStore.getState().setUserProfile({
            name: profile.name,
            email: profile.email,
            preferred_username: profile.preferred_username,
          });
        }
      } catch {
      }

      try {
        const me = await api.me();
        if (cancelled) return;
        setUserId(me.id);
      } catch {
        if (cancelled) return;
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [setToken, setUserId]);

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          
          <Route element={<DashboardLayout />}>
            <Route
              path="/"
              element={
                <HomePage userId={userId} setUserId={setUserId} />
              }
            />
            <Route path="/dashboard" element={<Navigate to="/" replace />} />
            <Route path="/movie/:movieId" element={<MovieDetail />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/rate" element={<RatePage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/profile" element={<ProfilePage />} />
          </Route>
        </Routes>
      </BrowserRouter>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}
