import Link from "next/link";
import type { EventsOutcome } from "@/lib/intel";
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
const HOW_MANY = 8;

/** Human labels for the persisted event types the feed emits. */
const EVENT_TYPE_LABELS: Record<string, string> = {
  audience_shift: "Audience shift",
  citation_source_shift: "Citation source shift",
  commerce_ads: "Commerce and ads",
  crawler_policy: "Crawler policy",
  referral_measurement: "Referral measurement",
};

function eventTypeLabel(value: string): string {
  return EVENT_TYPE_LABELS[value] ?? value.replace(/_/g, " ");
}

/** Best available date for an event, honest about absence. */
function eventDate(event: { effective_from?: string | null; published_at?: string | null; observed_at?: string | null }): string {
  return formatDate(event.effective_from ?? event.published_at ?? event.observed_at ?? null);
}

export function LandingChanges({ outcome }: { outcome: EventsOutcome }) {
  const items = outcome.items.slice(0, HOW_MANY);
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
        <Link className="landing-link" href="/surfaces" data-testid="landing-changes-more">
          Explore surfaces and evidence →
        </Link>
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
        <ol className="change-list" data-testid="change-list">
          {items.map((event) => (
            <li className="change-item" key={event.id} data-testid={`change-${event.id}`}>
              <div className="change-item-head">
                <span className="pill change-type">{eventTypeLabel(event.event_type)}</span>
                <span className="change-date">{eventDate(event)}</span>
              </div>
              <p className="change-title">{event.title}</p>
              {(event.surfaces ?? []).length ? (
                <p className="change-surfaces">
                  {(event.surfaces ?? []).map((surface) => (
                    <Link className="pill pill-surface" key={surface} href={`/surfaces?q=${encodeURIComponent(surface)}`}>
                      {surface}
                    </Link>
                  ))}
                </p>
              ) : null}
              {(event.claims ?? []).length ? (
                <p className="change-drill">
                  <Link href={evidenceHref((event.claims ?? [])[0])}>Evidence drill-down →</Link>
                </p>
              ) : null}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
