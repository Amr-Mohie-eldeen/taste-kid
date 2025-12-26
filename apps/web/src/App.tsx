import { useEffect, useState } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { api } from "./lib/api";
import { AppShell } from "./components/AppShell";
import { Dashboard } from "./pages/Dashboard";
import { MovieDetail } from "./pages/MovieDetail";

const STORAGE_KEY = "tastekid:userId";

export default function App() {
  const [apiStatus, setApiStatus] = useState<"checking" | "online" | "offline">(
    "checking"
  );
  const [userId, setUserId] = useState<number | null>(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? Number(stored) : null;
  });

  useEffect(() => {
    api
      .health()
      .then(() => setApiStatus("online"))
      .catch(() => setApiStatus("offline"));
  }, []);

  const handleSetUserId = (id: number | null) => {
    setUserId(id);
    if (id === null) {
      localStorage.removeItem(STORAGE_KEY);
    } else {
      localStorage.setItem(STORAGE_KEY, id.toString());
    }
  };

  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route
            path="/"
            element={
              <Dashboard apiStatus={apiStatus} userId={userId} setUserId={handleSetUserId} />
            }
          />
          <Route path="/movie/:movieId" element={<MovieDetail userId={userId} />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
