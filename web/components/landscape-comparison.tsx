"use client";

import Link from "next/link";
import { evidenceClassLabel } from "@/lib/mechanics";
import { MECHANICS_STATE_LABELS } from "@/lib/mechanics";
import type { LandscapeProjection, LandscapeSurface, ComparisonCell } from "@/lib/landscape";

/**
 * Mechanics comparison across 2-6 surfaces (issue #60). A dimension-per-row
 * matrix; each cell shows the surface's evidenced state with a one-line
 * statement and an evidence link, or an explicit "unknown" that is never
 * hidden. Registry facts and evidenced mechanics are kept distinct.
 */
function Cell({ surfaceId, cell }: { surfaceId: string; cell: ComparisonCell | undefined }) {
  if (!cell || cell.unknown) {
    return (
      <td className="cmp-cell cmp-unknown" data-testid={`cmp-${surfaceId}-unknown`}>
        <span className="cmp-unknown-badge">Unknown</span>
        <span className="cmp-unknown-note">No validated claim covers this dimension.</span>
      </td>
    );
  }
  return (
    <td className="cmp-cell" data-testid={`cmp-${surfaceId}-cell`}>
      <span className={`chip state-${cell.state}`}>{MECHANICS_STATE_LABELS[cell.state as keyof typeof MECHANICS_STATE_LABELS] ?? cell.state}</span>
      {cell.statement ? <p className="cmp-statement">{cell.statement}</p> : null}
      <p className="cmp-meta">
        {cell.evidence_class ? <span className="chip chip-class">{evidenceClassLabel(cell.evidence_class)}</span> : null}
        {cell.confidence ? <span className="muted"> · {cell.confidence} confidence</span> : null}
      </p>
      {cell.claim_id ? (
        <Link className="cmp-link" href={`/surfaces?surface=${encodeURIComponent(surfaceId)}`}>
          evidence →
        </Link>
      ) : null}
    </td>
  );
}

export function LandscapeComparison({
  projection,
  surfaces,
}: {
  projection: LandscapeProjection;
  surfaces: LandscapeSurface[];
}) {
  const ids = projection.comparison_surface_ids;
  return (
    <div className="cmp-wrap">
      <table className="cmp-table" data-testid="comparison-table">
        <caption className="cmp-caption">
          Discovery mechanics across {ids.length} surfaces. Unknown cells are explicit — the
          product never forces a false comparison.
        </caption>
        <thead>
          <tr>
            <th scope="col">Dimension</th>
            {ids.map((id) => {
              const s = surfaces.find((x) => x.id === id);
              return (
                <th key={id} scope="col" data-testid={`cmp-col-${id}`}>
                  <span className="cmp-col-name">{s?.name ?? id}</span>
                  <span className="cmp-col-vendor muted">{s?.vendor ?? ""}</span>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {projection.comparison.map((row) => (
            <tr key={row.dimension}>
              <th scope="row" className="cmp-row-head">
                <span className="cmp-dim-label">{row.label}</span>
                <span className="cmp-dim-def muted">{row.definition}</span>
              </th>
              {ids.map((id) => (
                <Cell key={id} surfaceId={id} cell={row.cells[id]} />
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
