import { Link, useLocation } from "react-router-dom";
import { cn } from "../lib/utils";
import { Button } from "./ui/button";
import { useStore } from "../lib/store";
import {
   Home,
   Search,
   History,
   Star,
   User,
   LogOut,
   Clapperboard,
 } from "lucide-react";

interface SidebarProps extends React.HTMLAttributes<HTMLDivElement> {
  onNavigate?: () => void;
  collapsed?: boolean;
}

export function Sidebar({ className, onNavigate, collapsed }: SidebarProps) {
  const location = useLocation();
  const { userProfile, resetSession } = useStore();

  const handleLogout = () => {
    resetSession();
    window.location.href = "/";
  };

   const navItems = [
     { name: "Home", href: "/", icon: Home },
     { name: "Search", href: "/search", icon: Search },
     { name: "Rate", href: "/rate", icon: Star },
     { name: "History", href: "/history", icon: History },
     { name: "Profile", href: "/profile", icon: User },
   ];

  return (
    <div className={cn("flex h-full flex-col border-r bg-zinc-950/50 backdrop-blur-xl", className)}>
       <div className={cn("flex h-14 items-center border-b border-zinc-800/50", collapsed ? "px-3 justify-center" : "px-6")}>
         <Link
           to="/"
           className={cn("flex items-center font-semibold text-white", collapsed ? "gap-0" : "gap-2")}
           onClick={onNavigate}
           title="Taste Kid"
         >
           <Clapperboard className="h-5 w-5 text-indigo-400" />
           {!collapsed && <span className="tracking-tight">Taste Kid</span>}
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
                title={collapsed ? item.name : undefined}
                className={cn(
                  "flex items-center rounded-md px-3 py-2.5 text-sm font-medium transition-all duration-200",
                  collapsed ? "justify-center" : "gap-3",
                  isActive
                    ? "bg-indigo-500/15 text-indigo-300"
                    : "text-zinc-300 hover:bg-white/5 hover:text-zinc-100"
                )}
              >
                <Icon
                  className={cn(
                    collapsed ? "h-5 w-5" : "h-4 w-4",
                    isActive ? "text-indigo-400" : "text-zinc-500 group-hover:text-zinc-100"
                  )}
                />
                {!collapsed && item.name}

              </Link>
            );
          })}
        </nav>
      </div>

      <div className={cn("mt-auto border-t border-zinc-800/50", collapsed ? "p-3" : "p-4")}>
        <div
          className={cn(
            "flex items-center justify-between gap-2 rounded-lg border border-zinc-800 bg-zinc-900/50",
            collapsed ? "p-2" : "p-3"
          )}
        >
          {!collapsed && (
            <div className="flex flex-col overflow-hidden">
              <span className="truncate text-xs font-medium text-zinc-200">
                {userProfile?.name || "Guest User"}
              </span>
              <span className="truncate text-[11px] text-zinc-300">
                {userProfile?.email || "Sign in to sync"}
              </span>
            </div>
          )}
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-zinc-400 hover:text-white hover:bg-white/5"
            onClick={handleLogout}
            title="Sign out"
          >
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
