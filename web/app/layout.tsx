import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Discovery Intelligence",
  description:
    "What changed, what matters and what we currently believe about how consumer AI discovery surfaces find, retrieve, cite and recommend information.",
};

// Marketer-first navigation (issue #61): the four user-facing concepts lead;
// internal architecture terms (POV, reconciliation) are demoted below a divider
// and reachable but no longer drive primary navigation.
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
            <ul>
              {NAV_PRIMARY.map((item) => (
                <li key={item.href}>
                  <Link href={item.href}>{item.label}</Link>
                </li>
              ))}
              {NAV_SECONDARY.map((item) => (
                <li key={item.href} className="site-nav-secondary">
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
