/** Read-only server-side projection; raw snapshots and secrets never reach the browser. */
export interface EvidenceItem {
  id: string;
  url: string;
  title: string;
  publisher: string | null;
  source_class: string;
  published_at: string | null;
  modified_at: string | null;
  observed_at: string;
  topics: string[];
  capture_hash: string;
  excerpt: string | null;
  validation_status: string;
  is_candidate: boolean;
}

export type EvidenceFeed =
  | { status: "ready"; items: EvidenceItem[]; total: number }
  | { status: "unavailable"; message: string };

export async function loadEvidenceFeed(): Promise<EvidenceFeed> {
  const endpoint = process.env.AI_DISCOVERY_API_URL;
  if (!endpoint) return { status: "unavailable", message: "The evidence service is not connected." };
  try {
    const response = await fetch(`${endpoint.replace(/\/$/, "")}/evidence?limit=100`, {
      cache: "no-store", signal: AbortSignal.timeout(8000),
    });
    if (!response.ok) throw new Error(`Evidence service returned ${response.status}`);
    const body = await response.json();
    if (!Array.isArray(body.items) || !Number.isInteger(body.total)) {
      throw new Error("Evidence service returned an unexpected response");
    }
    // Do not expose malformed source URLs as executable browser links.
    if (body.items.some((item: EvidenceItem) =>
      typeof item.id !== "string" || typeof item.title !== "string" ||
      typeof item.url !== "string" || !/^https?:\/\//i.test(item.url) ||
      typeof item.capture_hash !== "string" || !Array.isArray(item.topics)
    )) throw new Error("Evidence service returned an invalid record");
    return { status: "ready", items: body.items, total: body.total };
  } catch {
    // Never show backend addresses, SQL errors, credentials or raw response bodies.
    return { status: "unavailable", message: "Evidence is temporarily unavailable. This is a service failure, not an absence of evidence." };
  }
}

export function evidenceDate(value: string | null): string {
  if (!value) return "Unknown / not supplied";
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? "Unknown / invalid source date" :
    new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeZone: "UTC" }).format(date);
}
