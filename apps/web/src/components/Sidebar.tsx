import { Link, useLocation } from "react-router-dom";
import { cn } from "../lib/utils";
import { Button } from "./ui/button";
import { useStore } from "../lib/store";
import {
  Home,
  Search,
  History,
  User,
  LogOut,
  Clapperboard,
} from "lucide-react";

interface SidebarProps extends React.HTMLAttributes<HTMLDivElement> {
  onNavigate?: () => void;
}

export function Sidebar({ className, onNavigate }: SidebarProps) {
  const location = useLocation();
  const { userProfile, resetSession } = useStore();

  const handleLogout = () => {
    resetSession();
    window.location.href = "/";
  };

  const navItems = [
    { name: "Home", href: "/", icon: Home },
    { name: "Search", href: "/search", icon: Search },
    { name: "History", href: "/history", icon: History },
    { name: "Profile", href: "/profile", icon: User },
  ];

  return (
    <div className={cn("flex h-full flex-col border-r bg-zinc-950/50 backdrop-blur-xl", className)}>
      <div className="flex h-14 items-center px-6 border-b border-zinc-800/50">
        <Link to="/" className="flex items-center gap-2 font-semibold text-white" onClick={onNavigate}>
          <Clapperboard className="h-5 w-5 text-indigo-400" />
          <span className="tracking-tight">Taste Kid</span>
        </Link>
      </div>

      <div className="flex-1 overflow-auto py-4">
        <nav className="grid gap-1 px-3">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.href;
            return (
              <Link
                key={item.href}
                to={item.href}
                onClick={onNavigate}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-all duration-200",
                  isActive
                    ? "bg-indigo-500/10 text-indigo-400 shadow-[0_0_20px_rgba(99,102,241,0.1)]"
                    : "text-zinc-400 hover:bg-white/5 hover:text-zinc-100"
                )}
              >
                <Icon className={cn("h-4 w-4", isActive ? "text-indigo-400" : "text-zinc-500 group-hover:text-zinc-100")} />
                {item.name}
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="mt-auto border-t border-zinc-800/50 p-4">
        <div className="flex items-center justify-between gap-2 rounded-lg border border-zinc-800 bg-zinc-900/50 p-3">
          <div className="flex flex-col overflow-hidden">
            <span className="truncate text-xs font-medium text-zinc-200">
              {userProfile?.name || "Guest User"}
            </span>
            <span className="truncate text-[11px] text-zinc-300">
              {userProfile?.email || "Sign in to sync"}
            </span>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-zinc-400 hover:text-white hover:bg-white/5"
            onClick={handleLogout}
          >
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
