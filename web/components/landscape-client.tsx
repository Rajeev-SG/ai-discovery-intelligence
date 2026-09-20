"use client";

import { useEffect, useMemo, useState } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import { LandscapeGrid } from "@/components/landscape-grid";
import { LandscapeComparison } from "@/components/landscape-comparison";
import {
  DEFAULT_COMPARISON_IDS,
  COMPARISON_MAX,
  COMPARISON_MIN,
  parseComparisonIds,
  type LandscapeProjection,
} from "@/lib/landscape";
import Link from "next/link";

/**
 * Client shell for the landscape (issue #60). Holds the comparison selection in
 * URL state so a filtered comparison is shareable, and renders the primary grid
 * plus the mechanics comparison for the selected surfaces. It only renders the
 * backend projection; it never derives a mechanic.
 */
export function LandscapeClient({ projection }: { projection: LandscapeProjection }) {
  const searchParams = useSearchParams();
  const pathname = usePathname();

  const availableIds = projection.surfaces.map((s) => s.id);
  // Initial selection: the URL, else the curated default filtered to real ids.
  const initial = useMemo(() => {
    const fromUrl = parseComparisonIds(searchParams.get("compare"));
    const base = fromUrl.length >= COMPARISON_MIN ? fromUrl : [...DEFAULT_COMPARISON_IDS];
    return base.filter((id) => availableIds.includes(id)).slice(0, COMPARISON_MAX);
    
  }, [searchParams, availableIds]);

  const [selected, setSelected] = useState<Set<string>>(new Set(initial));

  // Persist the comparison selection to the URL (shareable), like the plane.
  useEffect(() => {
    const ids = availableIds.filter((id) => selected.has(id));
    const params = new URLSearchParams(searchParams.toString());
    if (ids.length >= COMPARISON_MIN) params.set("compare", ids.join(","));
    else params.delete("compare");
    const qs = params.toString();
    const next = qs ? `${pathname}?${qs}` : pathname;
    window.history.replaceState(null, "", next);
  }, [selected, availableIds, pathname, searchParams]);

  const toggle = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else if (next.size < COMPARISON_MAX) next.add(id);
      return next;
    });
  };

  const orderedSelected = availableIds.filter((id) => selected.has(id));
  const selectedSurfaces = projection.surfaces.filter((s) => selected.has(s.id));
  // Restrict the comparison rows/columns to the live selection, so toggling a
  // surface updates the matrix without a round trip (the projection already
  // carries every curated surface's cells).
  const scoped: LandscapeProjection = {
    ...projection,
    comparison_surface_ids: orderedSelected,
    comparison: projection.comparison.map((row) => ({
      ...row,
      cells: Object.fromEntries(orderedSelected.map((id) => [id, row.cells[id]])),
    })),
  };

  return (
    <>
      <section className="landscape-section">
        <h2>Major surfaces</h2>
        <p className="landscape-section-note">
          Registry facts (type, geography, discovery modes) are marked as registry
          metadata. Reach is a single evidenced figure where one exists; mechanics
          coverage and confidence come from validated claims only. Market share is
          context, not the product.{" "}
          <Link href="/surfaces">Explore the full 35-surface registry →</Link>
        </p>
        <LandscapeGrid surfaces={projection.surfaces} selected={selected} onToggle={toggle} />
      </section>

      <section className="landscape-section">
        <h2>Compare discovery mechanics</h2>
        <p className="landscape-section-note" data-testid="compare-status">
          Comparing {orderedSelected.length} surface{orderedSelected.length === 1 ? "" : "s"}
          {orderedSelected.length < COMPARISON_MIN
            ? ` — select at least ${COMPARISON_MIN} to compare.`
            : orderedSelected.length >= COMPARISON_MAX
              ? ` (maximum ${COMPARISON_MAX}).`
              : "."}{" "}
          The selection is stored in the URL, so the comparison is shareable.
        </p>
        {orderedSelected.length >= COMPARISON_MIN ? (
          <LandscapeComparison projection={scoped} surfaces={projection.surfaces} />
        ) : (
          <p className="landscape-empty" data-testid="compare-too-few">
            Select at least {COMPARISON_MIN} surfaces above to compare their mechanics.
          </p>
        )}
      </section>
    </>
  );
}
