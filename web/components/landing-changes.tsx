import Link from "next/link";
import { eventTypeLabel, type EventsOutcome } from "@/lib/intel";
import { formatDate } from "@/lib/evidence";
import { evidenceHref } from "@/lib/pov";

/**
 * Latest material changes (issue #45). Renders the newest persisted change
 * events from `GET /events`. It shows only fields the backend actually holds —
 * the event's own description is the material change; the event type is the
 * taxonomy label, not an invented implication — plus a drill-down into the
 * surface evidence for the claim behind the event. When the backend is
 * unreachable the section says so rather than showing a misleading empty list.
 */
export const HOW_MANY = 5;

/** Best available date for an event, honest about absence. */
function eventDate(event: { effective_from?: string | null; published_at?: string | null; observed_at?: string | null }): string {
  return formatDate(event.effective_from ?? event.published_at ?? event.observed_at ?? null);
}

/**
 * Compact change row: the whole row is the drill-down link, so there is no
 * separate "Evidence drill-down →" line repeated under every item. Type and
 * date share one meta line; surfaces are chips only when they add context.
 */
export function LandingChanges({ outcome }: { outcome: EventsOutcome }) {
  const items = outcome.items.slice(0, HOW_MANY);
  const total = outcome.items.length;
  return (
    <section className="landing-section" aria-labelledby="landing-changes-title" data-testid="landing-changes">
      <header className="landing-section-head">
        <div>
          <p className="eyebrow">Latest material changes</p>
          <h2 id="landing-changes-title">What changed</h2>
          <p className="landing-lede">
            The newest persisted change events against the surface registry, newest first.
          </p>
        </div>
      </header>

      {outcome.status === "error" || outcome.status === "unconfigured" ? (
        <p className="landing-state landing-state-error" data-testid="changes-unavailable">
          The change-event service is not reachable right now. No change is shown rather than
          inventing one.
        </p>
      ) : items.length === 0 ? (
        <p className="landing-state" data-testid="changes-empty">
          No material change event is currently recorded.
        </p>
      ) : (
        <>
          <ol className="change-list" data-testid="change-list">
            {items.map((event) => {
              const claim = (event.claims ?? [])[0];
              const surfaces = event.surfaces ?? [];
              return (
                <li className="change-item" key={event.id} data-testid={`change-${event.id}`}>
                  <div className="change-row">
                    <span className="change-meta">
                      <span className="change-type">{eventTypeLabel(event.event_type)}</span>
                      <span className="change-date">{eventDate(event)}</span>
                      {surfaces.length ? (
                        <span className="change-surfaces-inline">
                          <Link
                            className="change-surface-link"
                            href={`/surfaces?q=${encodeURIComponent(surfaces[0])}`}
                          >
                            {surfaces[0]}
                          </Link>
                          {surfaces.length > 1 ? ` +${surfaces.length - 1}` : ""}
                        </span>
                      ) : null}
                    </span>
                    {claim ? (
                      <Link className="change-title change-title-link" href={evidenceHref(claim)}>
                        {event.title}
                      </Link>
                    ) : (
                      <span className="change-title">{event.title}</span>
                    )}
                    {claim ? (
                      <span className="change-chevron" aria-hidden="true">
                        →
                      </span>
                    ) : null}
                  </div>
                </li>
              );
            })}
          </ol>
          {total > HOW_MANY ? (
            <p className="change-truncation" data-testid="changes-truncation">
              Showing the newest {HOW_MANY} of {total} changes.{" "}
              <Link href="/surfaces">All changes in Explore surfaces →</Link>
            </p>
          ) : null}
        </>
      )}
    </section>
  );
}
