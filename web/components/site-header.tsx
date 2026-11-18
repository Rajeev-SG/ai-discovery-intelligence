"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import styles from "./site-header.module.css";

// The site header, copied from rajeevg.com's public chrome (same wordmark,
// same nav, same sizes and spacing) so AI Discovery reads as one of the site's
// sections rather than a separate product. Every link points at the main site:
// this app is proxied under rajeevg.com/solutions/ai-discovery, so its own
// paths are not the site's paths.
const SITE_ORIGIN = "https://rajeevg.com";

const NAV = [
  { href: "/", label: "Home" },
  { href: "/solutions", label: "Solutions" },
  { href: "/interfaces", label: "Interfaces" },
  { href: "/blog", label: "Writing" },
  { href: "/about", label: "About" },
];

// Which section of the site this page belongs to. Solutions is the active item
// everywhere in this app; the surface pages and the home page are the light
// pages, so the header follows their palette instead of painting a dark bar
// above white content (and vice versa on the dark analysis pages).
const SURFACE_ROUTE = /\/surfaces(?:\/|$)/;
const HOME_ROUTE = /^(?:\/|\/solutions\/ai-discovery\/?)$/;

export function SiteHeader() {
  const pathname = usePathname() ?? "/";
  const light = HOME_ROUTE.test(pathname) || SURFACE_ROUTE.test(pathname);

  return (
    <header className={styles.header} data-palette={light ? "light" : "dark"} data-testid="site-header">
      <div className={styles.inner}>
        <Link className={styles.wordmark} href={SITE_ORIGIN}>
          Rajeev Gill
        </Link>

        <nav className={styles.nav} aria-label="Primary navigation">
          {NAV.map((item) => (
            <a
              key={item.href}
              className={styles.link}
              href={`${SITE_ORIGIN}${item.href}`}
              aria-current={item.label === "Solutions" ? "page" : undefined}
            >
              {item.label}
            </a>
          ))}
        </nav>

        {/* A native disclosure keeps the mobile menu working without JavaScript
            and mirrors the hamburger control on rajeevg.com. */}
        <details className={styles.menu}>
          <summary className={styles.menuButton} aria-label="Open navigation">
            <svg className={styles.menuIcon} viewBox="0 0 20 20" aria-hidden="true">
              <path d="M3 5h14M3 10h14M3 15h14" />
            </svg>
            <svg className={styles.closeIcon} viewBox="0 0 20 20" aria-hidden="true">
              <path d="M5 5l10 10M15 5L5 15" />
            </svg>
          </summary>
          <nav className={styles.mobileNav} aria-label="Mobile navigation">
            {NAV.map((item) => (
              <a
                key={item.href}
                className={styles.mobileLink}
                href={`${SITE_ORIGIN}${item.href}`}
                aria-current={item.label === "Solutions" ? "page" : undefined}
              >
                {item.label}
              </a>
            ))}
          </nav>
        </details>
      </div>
    </header>
  );
}
