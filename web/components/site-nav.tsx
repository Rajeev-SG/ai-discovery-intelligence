"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

/**
 * The site navigation (issue #69): an active-state indicator via
 * `aria-current="page"`, and Evidence reconciliation removed from the public
 * navigation — it is an internal research view, reachable only by direct URL
 * (its finding-level caveats render inline where they qualify a conclusion).
 */
const NAV_PRIMARY = [
  { href: "/", label: "Home" },
  { href: "/landscape", label: "Landscape" },
  { href: "/implications", label: "Marketing implications" },
  { href: "/surfaces", label: "Explore surfaces" },
];
const NAV_SECONDARY = [{ href: "/pov", label: "What this means" }];

export function SiteNav() {
  const pathname = usePathname();
  const isCurrent = (href: string) =>
    href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
  return (
    <nav className="site-nav" aria-label="Product surfaces">
      <Link className="site-nav-brand" href="/">
        AI Discovery Intelligence
      </Link>
      <ul className="site-nav-primary">
        {NAV_PRIMARY.map((item) => (
          <li key={item.href}>
            <Link href={item.href} aria-current={isCurrent(item.href) ? "page" : undefined}>
              {item.label}
            </Link>
          </li>
        ))}
      </ul>
      <ul className="site-nav-secondary" aria-label="More">
        {NAV_SECONDARY.map((item) => (
          <li key={item.href}>
            <Link href={item.href} aria-current={isCurrent(item.href) ? "page" : undefined}>
              {item.label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}