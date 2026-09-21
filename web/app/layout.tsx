import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Discovery Intelligence",
  description:
    "Which AI discovery platforms matter, how their search and retrieval work, how strong the evidence is, and what it means for marketers — built on source-backed mechanics.",
};

// Marketer-first navigation (issue #61): the four user-facing concepts lead;
// internal architecture terms (POV, reconciliation) are grouped into a separate,
// visually divided "More" list so they no longer sit in the primary nav bar.
const NAV_PRIMARY = [
  { href: "/", label: "Home" },
  { href: "/landscape", label: "Landscape" },
  { href: "/implications", label: "Marketing implications" },
  { href: "/surfaces", label: "Explore surfaces" },
];
const NAV_SECONDARY = [
  { href: "/pov", label: "What this means" },
  { href: "/reconciliation", label: "Evidence reconciliation" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en-GB">
      <body>
        <a className="skip-link" href="#content">
          Skip to content
        </a>
        <div className="page-shell">
          <nav className="site-nav" aria-label="Product surfaces">
            <Link className="site-nav-brand" href="/">
              AI Discovery Intelligence
            </Link>
            <ul className="site-nav-primary">
              {NAV_PRIMARY.map((item) => (
                <li key={item.href}>
                  <Link href={item.href}>{item.label}</Link>
                </li>
              ))}
            </ul>
            <ul className="site-nav-secondary" aria-label="More">
              {NAV_SECONDARY.map((item) => (
                <li key={item.href}>
                  <Link href={item.href}>{item.label}</Link>
                </li>
              ))}
            </ul>
          </nav>
          <main id="content">{children}</main>
        </div>
      </body>
    </html>
  );
}
