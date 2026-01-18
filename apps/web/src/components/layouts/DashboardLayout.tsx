import { useState } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "../Sidebar";
import { Menu, X, PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { Button } from "../ui/button";

export function DashboardLayout() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  return (
    <div className="min-h-screen bg-zinc-950 font-sans selection:bg-indigo-500/30 text-zinc-100">
      <div className={isSidebarCollapsed ? "hidden md:fixed md:inset-y-0 md:flex md:w-16 md:flex-col" : "hidden md:fixed md:inset-y-0 md:flex md:w-64 md:flex-col"}>
        <Sidebar collapsed={isSidebarCollapsed} />
      </div>

      <div className="md:hidden fixed top-0 left-0 right-0 z-50 flex h-14 items-center justify-between border-b border-zinc-800 bg-zinc-950/80 px-4 backdrop-blur-xl">
        <div className="flex items-center gap-2 font-semibold">
          <span className="text-lg tracking-tight">Taste Kid</span>
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          className="text-zinc-400 hover:text-white"
        >
          {isMobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </Button>
      </div>

      {isMobileMenuOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div 
            className="absolute inset-0 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200"
            onClick={() => setIsMobileMenuOpen(false)}
          />
          <div className="absolute inset-y-0 left-0 w-3/4 max-w-xs animate-in slide-in-from-left duration-200">
             <Sidebar onNavigate={() => setIsMobileMenuOpen(false)} className="h-full border-r border-zinc-800 bg-zinc-950" />
          </div>
        </div>
      )}

      <div className={isSidebarCollapsed ? "flex min-h-screen flex-col md:pl-16" : "flex min-h-screen flex-col md:pl-64"}>
        <div className="hidden md:flex h-14 items-center justify-between border-b border-zinc-800/60 bg-zinc-950/60 px-4 backdrop-blur-xl">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setIsSidebarCollapsed((v) => !v)}
            className="text-zinc-400 hover:text-white hover:bg-white/5"
            title={isSidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {isSidebarCollapsed ? (
              <PanelLeftOpen className="h-5 w-5" />
            ) : (
              <PanelLeftClose className="h-5 w-5" />
            )}
          </Button>
          <div className="text-sm text-zinc-400">Taste Kid</div>
          <div className="w-10" />
        </div>

        <main className="flex-1 pt-14 md:pt-0">
          <div className="mx-auto max-w-7xl p-6 md:p-8 animate-in fade-in duration-500">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
