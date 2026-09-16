import { ObservationPlane } from "@/components/observation-plane";
import { loadRegistry } from "@/lib/registry";
import { toSurfaceRows } from "@/lib/surfaces";

export const dynamic = "force-dynamic";

export default function Page() {
  const registry = loadRegistry();
  const rows = toSurfaceRows(registry);
  return (
    <ObservationPlane rows={rows} registryVersion={registry.version} lastReviewed={registry.lastReviewed} />
  );
}
