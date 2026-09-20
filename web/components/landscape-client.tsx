"use client";

import { useCallback, useEffect, useState } from "react";
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
  const availableKey = availableIds.join(",");

  // Read the LIVE url at action time. `useSearchParams()` is a render-time
  // snapshot that a `history.replaceState` write does not update, so building the
  // next URL from it would drop any other live query parameter (issue #60 review).
  const liveCompare = useCallback((): string | null => {
    if (typeof window === "undefined") return searchParams.get("compare");
    return new URLSearchParams(window.location.search).get("compare");
  }, [searchParams]);

  const selectFrom = useCallback(
    (raw: string | null): Set<string> => {
      const available = availableKey ? availableKey.split(",") : [];
      if (raw === null) {
        return new Set([...DEFAULT_COMPARISON_IDS].filter((id) => available.includes(id)));
      }
      return new Set(parseComparisonIds(raw).filter((id) => available.includes(id)));
    },
    [availableKey],
  );

  const [selected, setSelected] = useState<Set<string>>(() =>
    selectFrom(searchParams.get("compare")),
  );

  // The URL is the source of truth for EXTERNAL navigation. Back/forward fires a
  // popstate (which `replaceState` does not), so subscribing to it re-derives the
  // selection from the live URL — a shared link and history navigation always
  // agree with what is shown.
  useEffect(() => {
    const onPop = () => setSelected(selectFrom(liveCompare()));
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, [selectFrom, liveCompare]);

  const toggle = (id: string) => {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else if (next.size < COMPARISON_MAX) next.add(id);
    setSelected(next);
    // Build the next URL from the LIVE query at action time, so any other live
    // parameter (utm_*, etc.) survives; always write `compare` so it round-trips.
    const ids = availableIds.filter((x) => next.has(x));
    const params = new URLSearchParams(
      typeof window !== "undefined" ? window.location.search : "",
    );
    params.set("compare", ids.join(","));
    if (typeof window !== "undefined") {
      window.history.replaceState(null, "", `${pathname}?${params.toString()}`);
    }
  };

  // Ids present in a shared URL that are not in this curated landscape are dropped
  // (never fetched). Surface that explicitly rather than silently narrowing the
  // comparison (issue #60 review: client and /landscape/comparison must not
  // diverge silently; the endpoint is the validated API path).
  // Use the render-time param here (not window) so SSR and hydration agree; the
  // dropped-id notice is about a pasted/shared link, which `searchParams` carries.
  const requestedIds = parseComparisonIds(searchParams.get("compare"));
  const droppedIds = requestedIds.filter((id) => !availableIds.includes(id));

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
          {droppedIds.length ? (
            <span className="cmp-dropped" data-testid="compare-dropped">
              {" "}
              Ignored {droppedIds.length} id{droppedIds.length === 1 ? "" : "s"} not in
              this landscape ({droppedIds.join(", ")}).
            </span>
          ) : null}
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
