import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Discovery Intelligence",
  description:
    "What changed, what matters and what we currently believe about how consumer AI discovery surfaces find, retrieve, cite and recommend information.",
};

const NAV = [
  { href: "/", label: "Intelligence" },
  { href: "/surfaces", label: "Explore surfaces" },
  { href: "/pov", label: "POV" },
  { href: "/reconciliation", label: "Reconciliation" },
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
              {NAV.map((item) => (
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
