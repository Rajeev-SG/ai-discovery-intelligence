"use client";

import Link from "next/link";
import { coverageLabel, type LandscapeSurface } from "@/lib/landscape";

/**
 * The primary marketer-facing landscape (issue #60). A card/grid of the major
 * consumer AI discovery surfaces: name/vendor, type, priority/geography,
 * evidence reach where it exists, discovery modes, mechanics
 * coverage/confidence and a one-line relevance. Registry facts are labelled as
 * registry metadata; reach is a single contextual figure, never the organising
 * layer. Selecting a surface links into the comparison.
 */
export function LandscapeGrid({
  surfaces,
  selected,
  onToggle,
}: {
  surfaces: LandscapeSurface[];
  selected: Set<string>;
  onToggle: (id: string) => void;
}) {
  return (
    <div className="landscape-grid" data-testid="landscape-grid">
      {surfaces.map((s) => {
        const isSelected = selected.has(s.id);
        const evidenced = s.evidenced_dimensions > 0;
        return (
          <article key={s.id} className="landscape-card" data-testid={`landscape-${s.id}`}>
            <header className="landscape-card-head">
              <div>
                <h3>{s.name}</h3>
                <p className="landscape-vendor">{s.vendor}</p>
              </div>
              <label className="landscape-compare-toggle">
                <input
                  type="checkbox"
                  checked={isSelected}
                  onChange={() => onToggle(s.id)}
                  data-testid={`compare-toggle-${s.id}`}
                  aria-label={`Include ${s.name} in the comparison`}
                />
                <span>Compare</span>
              </label>
            </header>

            <dl className="landscape-facts">
              <div>
                <dt>Type</dt>
                <dd>{s.type_label}</dd>
              </div>
              <div>
                <dt>Priority</dt>
                <dd>{s.priority}</dd>
              </div>
              <div>
                <dt>Geography</dt>
                <dd>{s.regions.join(", ") || "unknown"}</dd>
              </div>
              <div>
                <dt>Reach (evidenced)</dt>
                <dd>
                  {s.reach_metric ? (
                    <>
                      {s.reach_metric}
                      {s.reach_claim_id ? (
                        <>
                          {" "}
                          <Link
                            className="landscape-evidence-link"
                            href={`/surfaces?surface=${encodeURIComponent(s.id)}`}
                          >
                            evidence
                          </Link>
                        </>
                      ) : null}
                    </>
                  ) : (
                    <span className="muted">No evidenced reach figure</span>
                  )}
                </dd>
              </div>
            </dl>

            <p className="landscape-modes">
              <span className="muted">Discovery modes (registry):</span>{" "}
              {s.discovery_modes.map((m) => m.replace(/_/g, " ")).join(" · ") || "unknown"}
            </p>

            <p className={`landscape-coverage ${evidenced ? "is-evidenced" : "is-unknown"}`}>
              <strong>Mechanics coverage:</strong> {coverageLabel(s)}
              {s.coverage.conflicting ? ` · ${s.coverage.conflicting} conflicting` : ""}
              {evidenced ? "" : " · unknown is a valid answer"}
            </p>

            <p className="landscape-relevance">{s.relevance}</p>

            <Link className="landscape-open" href={`/surfaces?surface=${encodeURIComponent(s.id)}`}>
              Open evidence &amp; mechanics →
            </Link>
          </article>
        );
      })}
    </div>
  );
}
