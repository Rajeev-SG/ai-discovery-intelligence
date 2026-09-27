import type { Metadata } from "next";
import { SiteNav } from "@/components/site-nav";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Discovery Intelligence",
  description:
    "Which AI discovery platforms matter, how their search and retrieval work, how strong the evidence is, and what it means for marketers — built on source-backed mechanics.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en-GB">
      <body>
        <a className="skip-link" href="#content">
          Skip to content
        </a>
        <div className="page-shell">
          <SiteNav />
          <main id="content">{children}</main>
        </div>
      </body>
    </html>
  );
}
