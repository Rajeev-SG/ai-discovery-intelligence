"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { EvidenceDetail } from "@/components/evidence-detail";
import { MechanicsTrustPanel } from "@/components/mechanics-trust";
import type { SurfaceRow } from "@/lib/surfaces";

interface DetailDrawerProps {
  row: SurfaceRow | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  label: string;
  /**
   * A specific finding to highlight (issue #69): a `?evidence=<claim>` link
   * opens the panel on that claim, scrolled into view.
   */
  highlightClaimId?: string | null;
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="detail-section">
      <h3>{title}</h3>
      {children}
    </section>
  );
}

function ChipList({ values, empty }: { values: string[]; empty: string }) {
  if (!values.length) return <p className="detail-empty">{empty}</p>;
  return (
    <ul className="chip-list">
      {values.map((value) => (
        <li key={value} className="chip">
          {value}
        </li>
      ))}
    </ul>
  );
}

/**
 * Expansion panel for a row or an evidence-bearing cell. Registry facts are
 * shown verbatim; unknown retrieval architecture and missing evidence are shown
 * as explicit information rather than as blank cells.
 */
export function DetailDrawer({ row, open, onOpenChange, label, highlightClaimId }: DetailDrawerProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="drawer-overlay" />
        <Dialog.Content className="drawer-content" aria-describedby={undefined}>
          {row ? (
            <>
              <header className="drawer-header">
                <div>
                  <Dialog.Title className="drawer-title">{row.name}</Dialog.Title>
                  <p className="drawer-subtitle">
                    {row.vendor} · {row.family} · {row.typeLabel}
                  </p>
                </div>
                <Dialog.Close className="drawer-close" aria-label="Close detail panel">
                  Close
                </Dialog.Close>
              </header>

              <div className="drawer-meta">
                <span className="pill pill-tier">{row.tierLabel}</span>
                <span className={`pill pill-status status-${row.retrievalStatus}`}>{row.retrievalStatusLabel}</span>
                <span className="pill pill-evidence">{row.evidenceLabel}</span>
              </div>

              <div className="drawer-body">
                {/* Evidence first (issue #69): the decision-useful material leads;
                    registry facts (geography/distribution/modes) follow. The
                    drawer no longer repeats the inline row's retrieval-unknowns
                    registry notes — that duplication amplified every profile. */}
                <Section title="Evidence & trust">
                  <p className="detail-lead">
                    How we know this, how strong the evidence is, and where sources disagree —
                    grouped by discovery-mechanics dimension. Each finding carries its publisher,
                    public source, evidence class, dates, confidence and methodology.
                  </p>
                  <MechanicsTrustPanel surfaceId={row.id} />
                </Section>

                <Section title="Registry profile (metadata, not evidence)">
                  <ChipList values={row.regionLabels} empty="No region recorded in the registry." />
                  <p className="muted">
                    {row.distributionLabels.join(" · ") || "No distribution channel recorded."} —{" "}
                    {row.discoveryModeLabels.join(" · ") || "No discovery mode recorded."}
                  </p>
                  <p className="detail-hint">
                    Registry status: {row.retrievalStatusLabel}. This is a coarse registry
                    scorecard, not an evidenced mechanics finding.
                  </p>
                </Section>

                <Section title="Official URLs">
                  {row.officialUrls.length ? (
                    <ul className="url-list">
                      {row.officialUrls.map((url) => (
                        <li key={url}>
                          <a href={url} target="_blank" rel="noreferrer noopener">
                            {url}
                          </a>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="detail-empty">No official URL recorded.</p>
                  )}
                </Section>

                <EvidenceDetail surfaceId={row.id} highlightClaimId={highlightClaimId} />
              </div>
            </>
          ) : null}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export type { DetailDrawerProps };
export const drawerLabelPrefix = "detail";
