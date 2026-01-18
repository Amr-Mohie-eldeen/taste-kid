import { useEffect } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { api } from "./lib/api";
import { AppShell } from "./components/AppShell";
import { Dashboard } from "./pages/Dashboard";
import { Login } from "./pages/Login";
import { MovieDetail } from "./pages/MovieDetail";
import { Signup } from "./pages/Signup";
import { useStore } from "./lib/store";
import { queryClient } from "./lib/queryClient";

export default function App() {
  const { resetSession, setApiStatus, setUserId, token, userId } = useStore();

  useEffect(() => {
    api
      .health()
      .then(() => setApiStatus("online"))
      .catch(() => setApiStatus("offline"));
  }, [setApiStatus]);

  useEffect(() => {
    if (userId && !token) {
      resetSession();
    }
  }, [resetSession, token, userId]);

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<AppShell />}>
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
            <Route
              path="/"
              element={
                <Dashboard userId={userId} setUserId={setUserId} />
              }
            />
            <Route path="/movie/:movieId" element={<MovieDetail />} />
          </Route>
        </Routes>
      </BrowserRouter>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}