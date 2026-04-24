import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";

import { SessionProvider } from "../components/session-provider";
import { SiteShell } from "../components/site-shell";

export const metadata: Metadata = {
  title: "Streamline Live",
  description: "Browse live streams, launch your studio, and join live sessions.",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <SessionProvider>
          <SiteShell>{children}</SiteShell>
        </SessionProvider>
      </body>
    </html>
  );
}
