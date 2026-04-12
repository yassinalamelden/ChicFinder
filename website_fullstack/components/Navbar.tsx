"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { LogOut } from "lucide-react";

const NAV_LINKS = [
  { href: "/", label: "Home" },
  { href: "/stores", label: "Stores" },
];

export function Navbar() {
  const pathname = usePathname();
  const { user, signOut } = useAuth();

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 py-4 border-b border-white/10 bg-black/60 backdrop-blur-md">
      {/* Logo */}
      <Link href="/" className="text-sm font-semibold tracking-widest text-white/90 uppercase hover:text-white transition-colors">
        ChicFinder
      </Link>

      {/* Nav links */}
      <div className="flex items-center gap-6">
        {NAV_LINKS.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className={`text-sm transition-colors ${
              pathname === link.href
                ? "text-white"
                : "text-white/50 hover:text-white"
            }`}
          >
            {link.label}
          </Link>
        ))}
      </div>

      {/* User */}
      <div className="flex items-center gap-3">
        {user && (
          <>
            <span className="text-xs text-white/40 hidden sm:block truncate max-w-[140px]">
              {user.displayName ?? user.email}
            </span>
            <button
              onClick={signOut}
              className="flex items-center gap-1.5 text-xs text-white/50 hover:text-white transition-colors"
              aria-label="Sign out"
            >
              <LogOut className="w-4 h-4" />
              <span className="hidden sm:inline">Sign out</span>
            </button>
          </>
        )}
      </div>
    </nav>
  );
}
