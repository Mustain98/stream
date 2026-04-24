"use client";

import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect } from "react";

import { useSession } from "./session-provider";

export function RequireAuth({ children }: { children: ReactNode }) {
  const { user, isLoading } = useSession();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !user) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [isLoading, pathname, router, user]);

  if (isLoading || !user) {
    return (
      <section className="center-card">
        <p className="eyebrow">Checking session</p>
        <h1>Locking in your access to the stream room.</h1>
      </section>
    );
  }

  return <>{children}</>;
}
