/**
 * Server-only surface name resolution (issue #69): the reading layer shows
 * human platform names, never raw registry slugs. Used by server components
 * (landing sections); client components must receive names via props.
 */
import { loadRegistry } from "@/lib/registry";

let cached: Record<string, string> | null = null;

export function surfaceNames(): Record<string, string> {
  if (cached) return cached;
  const registry = loadRegistry();
  cached = Object.fromEntries(registry.surfaces.map((s) => [s.id, s.name]));
  return cached;
}

/** Human name for a surface id, falling back to the id itself. */
export function surfaceName(id: string): string {
  return surfaceNames()[id] ?? id;
}