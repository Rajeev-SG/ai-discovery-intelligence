"use server";

/**
 * Server action backing the drill-down. Called from the client only when a
 * drawer opens, so the full claim/provenance payload is fetched on demand
 * instead of being shipped for every surface up front.
 */
import { fetchSurfaceDetail, type SurfaceDetail } from "@/lib/evidence";

export async function loadSurfaceDetail(surfaceId: string): Promise<SurfaceDetail> {
  return fetchSurfaceDetail(surfaceId);
}
