"use server";

/**
 * Server action backing the evidence & trust layer's mechanics section (issue
 * #58). Called from the client only when a surface's drill-down opens, so the
 * per-surface mechanics projection (with its inline reconciliation) is fetched
 * on demand rather than shipped for every surface up front. Results are memoized
 * per surface for a short TTL, and a failed fetch is not cached, so an
 * unreachable backend is retried rather than pinned as "no mechanics".
 */
import { fetchSurfaceMechanics, type SurfaceMechanicsOutcome } from "@/lib/mechanics";

const TTL_MS = 60_000;
const cache = new Map<string, { at: number; value: SurfaceMechanicsOutcome }>();

export async function loadSurfaceMechanics(surfaceId: string): Promise<SurfaceMechanicsOutcome> {
  const hit = cache.get(surfaceId);
  const now = Date.now();
  if (hit && now - hit.at < TTL_MS && hit.value.status !== "error") {
    return hit.value;
  }
  const value = await fetchSurfaceMechanics(surfaceId);
  if (value.status !== "error") cache.set(surfaceId, { at: now, value });
  return value;
}
