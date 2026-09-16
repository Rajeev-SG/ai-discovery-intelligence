import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Discovery Intelligence — Observation plane",
  description:
    "A source-backed view of how consumer AI discovery surfaces find, retrieve, cite and recommend information.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en-GB">
      <body>
        <a className="skip-link" href="#plane-main">
          Skip to the surface registry
        </a>
        <div className="page-shell">
          <nav className="site-nav" aria-label="Product surfaces">
            <span className="site-nav-brand">AI Discovery Intelligence</span>
            <ul>
              <li>
                <span aria-current="page">Observation plane</span>
              </li>
              <li aria-disabled="true">
                <span className="nav-coming-soon">Weekly brief (issue 06)</span>
              </li>
              <li aria-disabled="true">
                <span className="nav-coming-soon">Living POV (issue 07)</span>
              </li>
            </ul>
          </nav>
          <main id="plane-main">{children}</main>
        </div>
      </body>
    </html>
  );
}
