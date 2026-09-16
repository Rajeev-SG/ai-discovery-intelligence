"use client";

import * as Dialog from "@radix-ui/react-dialog";
import type { SurfaceRow } from "@/lib/surfaces";

interface DetailDrawerProps {
  row: SurfaceRow | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  label: string;
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
export function DetailDrawer({ row, open, onOpenChange, label }: DetailDrawerProps) {
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
                <Section title="Geography">
                  <ChipList values={row.regionLabels} empty="No region recorded in the registry." />
                </Section>

                <Section title="Distribution channels">
                  <ChipList values={row.distributionLabels} empty="No distribution channel recorded yet." />
                </Section>

                <Section title="Discovery modes">
                  <ChipList values={row.discoveryModeLabels} empty="No discovery mode recorded yet." />
                </Section>

                <Section title="Retrieval architecture">
                  <p className="detail-lead">
                    Registry status: <strong>{row.retrievalStatusLabel}</strong>.{" "}
                    {row.retrievalUnknown
                      ? "The retrieval stack below is genuinely unknown — this is information, not a missing value."
                      : "Some behaviour is documented; the gaps below are still not evidenced."}
                  </p>
                  <ul className="unknown-list">
                    {row.retrievalUnknownNotes.map((note) => (
                      <li key={note}>{note}</li>
                    ))}
                  </ul>
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

                <Section title="Evidence">
                  <p className="detail-lead">
                    <strong>{row.evidenceLabel}.</strong> {row.evidenceNote}
                  </p>
                  <dl className="evidence-grid">
                    <div>
                      <dt>Claims</dt>
                      <dd className="placeholder">Awaiting ingestion (issue 03)</dd>
                    </div>
                    <div>
                      <dt>Methodology</dt>
                      <dd className="placeholder">Awaiting ingestion (issue 02)</dd>
                    </div>
                    <div>
                      <dt>Conflicting evidence</dt>
                      <dd className="placeholder">Awaiting ingestion (issue 04)</dd>
                    </div>
                    <div>
                      <dt>Confidence</dt>
                      <dd className="placeholder">{row.confidenceLabel}</dd>
                    </div>
                    <div>
                      <dt>Last verified</dt>
                      <dd className="placeholder">Not yet verified — registry reviewed {row.lastReviewed}</dd>
                    </div>
                  </dl>
                </Section>
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
