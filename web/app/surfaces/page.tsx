import type { Metadata } from "next";
import { ObservationPlane } from "@/components/observation-plane";
import { applyEvidence, fetchSurfaceEvidence } from "@/lib/evidence";
import { loadRegistry } from "@/lib/registry";
import { toSurfaceRows } from "@/lib/surfaces";

export const metadata: Metadata = {
  title: "Explore surfaces — AI Discovery Intelligence",
  description:
    "The full 35-surface registry: every consumer AI discovery surface, searchable, sortable and filterable, with the evidence held against each.",
};

export const dynamic = "force-dynamic";

/**
 * Explore surfaces (issue #45). The 35-surface registry matrix moved off the
 * homepage; it retains its TanStack search/sort/filter/facet/column behaviour
 * and the per-surface evidence drill-down.
 */
export default async function SurfacesPage() {
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
