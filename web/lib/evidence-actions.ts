"use server";

/**
 * Server action backing the drill-down. Called from the client only when a
 * drawer opens, so the full claim/provenance payload is fetched on demand
 * instead of being shipped for every surface up front. Results are memoized
 * per surface for a short TTL so reopening a drawer does not refetch.
 */
import { fetchSurfaceDetail, type SurfaceDetail } from "@/lib/evidence";

const TTL_MS = 60_000;
const cache = new Map<string, { at: number; value: SurfaceDetail }>();

export async function loadSurfaceDetail(surfaceId: string): Promise<SurfaceDetail> {
  const hit = cache.get(surfaceId);
  const now = Date.now();
  // Serve a cached success. A failed primary endpoint is not cached, so it is
  // retried on the next open instead of being pinned as a "no evidence" state.
  if (hit && now - hit.at < TTL_MS && hit.value.status.evidence !== "error") {
    return hit.value;
  }
  const value = await fetchSurfaceDetail(surfaceId);
  if (value.status.evidence !== "error") cache.set(surfaceId, { at: now, value });
  return value;
}
