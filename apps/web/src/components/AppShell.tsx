import { Outlet } from "react-router-dom";
import { NavBar } from "./NavBar";

export function AppShell() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-white to-surface">
      <NavBar />
      <main className="mx-auto max-w-6xl px-6 pb-16 pt-8">
        <div className="page-fade">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
