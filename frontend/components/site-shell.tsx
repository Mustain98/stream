"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ReactNode } from "react";

import { useSession } from "./session-provider";

function isActive(pathname: string, href: string) {
  if (href === "/") {
    return pathname === "/";
  }

  return pathname.startsWith(href);
}

export function SiteShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { user, signOut } = useSession();

  return (
    <div className="page-shell">
      <header className="topbar">
        <Link href="/" className="brand">
          Streamline Live
        </Link>
        <nav className="nav">
          <Link className={isActive(pathname, "/") ? "nav-link active" : "nav-link"} href="/">
            Live
          </Link>
          <Link
            className={isActive(pathname, "/studio") ? "nav-link active" : "nav-link"}
            href="/studio"
          >
            Studio
          </Link>
          {user ? (
            <>
              <Link
                className={isActive(pathname, "/profile") ? "nav-link active" : "nav-link"}
                href="/profile"
              >
                Dashboard
              </Link>
              <span className="user-pill">{user.username}</span>
              <button className="ghost-button" onClick={signOut} type="button">
                Sign out
              </button>
            </>
          ) : (
            <>
              <Link className="nav-link" href="/login">
                Log in
              </Link>
              <Link className="primary-button compact" href="/signup">
                Join now
              </Link>
            </>
          )}
        </nav>
      </header>
      <main>{children}</main>
    </div>
  );
}
