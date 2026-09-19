import { ObservationPlane } from "@/components/observation-plane";
import { applyEvidence, fetchSurfaceEvidence } from "@/lib/evidence";
import { loadRegistry } from "@/lib/registry";
import { toSurfaceRows } from "@/lib/surfaces";

export const dynamic = "force-dynamic";

export default async function Page() {
  const registry = loadRegistry();
  const rows = toSurfaceRows(registry);
  // Overlay real evidence when the evidence service is configured; otherwise the
  // plane keeps its explicit no-evidence state.
  const bySurface = await fetchSurfaceEvidence();
  const withEvidence = applyEvidence(rows, bySurface);
  return (
    <ObservationPlane
      rows={withEvidence}
      registryVersion={registry.version}
      lastReviewed={registry.lastReviewed}
    />
  );
}
