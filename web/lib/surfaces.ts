/**
 * Client-safe projection of the canonical surface registry. Contains no Node
 * built-ins, so it can be imported from client components. The YAML loader
 * lives in `registry.ts` and is server-only.
 */
/** Raw shape of one entry in config/surfaces.yaml (the canonical registry). */
export interface RegistrySurface {
  id: string;
  vendor: string;
  name: string;
  family: string;
  type: string;
  tier: string;
  regions: string[];
  distribution: string[];
  discovery_modes: string[];
  retrieval_status: string;
  official_urls: string[];
}

export interface Registry {
  version: number;
  lastReviewed: string;
  surfaces: RegistrySurface[];
}

/**
 * A surface row as rendered by the observation plane. Registry facts are kept
 * verbatim; evidence fields carry whatever the read-only evidence API holds for
 * the surface, or an explicit no-evidence state when it holds nothing.
 */
export interface SurfaceRow {
  id: string;
  name: string;
  vendor: string;
  family: string;
  type: string;
  typeLabel: string;
  tier: string;
  tierLabel: string;
  priorityRank: number;
  regions: string[];
  regionLabels: string[];
  distribution: string[];
  distributionLabels: string[];
  discoveryModes: string[];
  discoveryModeLabels: string[];
  retrievalStatus: string;
  retrievalStatusLabel: string;
  /** True when the registry itself flags retrieval as unknown/undocumented. */
  retrievalUnknown: boolean;
  retrievalUnknownNotes: string[];
  officialUrls: string[];
  evidenceStatus: "evidenced" | "no_evidence";
  evidenceLabel: string;
  evidenceNote: string;
  confidenceLabel: string;
  freshnessLabel: string;
  /** Number of validated claims backing this surface (0 = explicit no-evidence). */
  evidenceClaimCount: number;
  lastReviewed: string;
  /** Pre-built lowercase haystack covering every searchable field. */
  searchHaystack: string;
}


/**
 * Commercial priority ordering. `tier` is the registry's own field; this is a
 * presentation rank derived from it, not new evidence.
 */
export const TIER_LABELS: Record<string, string> = {
  core_global: "Core — global",
  core_china: "Core — China",
  core_regional: "Core — regional",
  secondary_global: "Secondary — global",
  watch_global: "Watch — global",
  watch_regional: "Watch — regional",
  watch_commerce: "Watch — commerce",
};

export const TIER_PRIORITY: Record<string, number> = {
  core_global: 1,
  core_china: 2,
  core_regional: 3,
  secondary_global: 4,
  watch_global: 5,
  watch_regional: 6,
  watch_commerce: 7,
};

export const TYPE_LABELS: Record<string, string> = {
  conversational_assistant: "Conversational assistant",
  ai_native_search: "AI-native search",
  search_augmentation: "Search augmentation",
  embedded_ecosystem_assistant: "Embedded ecosystem assistant",
  browser_native_ai: "Browser-native AI",
  general_consumer_agent: "General consumer agent",
  multi_model_assistant: "Multi-model assistant",
  commerce_native_ai: "Commerce-native AI",
};

export const REGION_LABELS: Record<string, string> = {
  global: "Global",
  china: "China",
  europe: "Europe",
  japan: "Japan",
  south_korea: "South Korea",
  russia: "Russia",
  cis: "CIS",
  multi_market: "Multi-market",
};

export const RETRIEVAL_STATUS_LABELS: Record<string, string> = {
  documented_in_part: "Documented in part",
  partially_documented: "Partially documented",
  under_documented: "Under-documented",
  heterogeneous: "Heterogeneous",
};

export function titleise(value: string): string {
  return value
    .split("_")
    .map((part) => (part.length <= 2 ? part.toUpperCase() : part[0].toUpperCase() + part.slice(1)))
    .join(" ");
}

function label(map: Record<string, string>, value: string): string {
  return map[value] ?? titleise(value);
}

/**
 * Unknowns are derived from the registry's own retrieval_status. This is
 * information, not an empty cell: the plane states exactly what is not yet
 * documented instead of implying anything.
 */
export function retrievalUnknowns(status: string): string[] {
  switch (status) {
    case "under_documented":
      return [
        "Upstream retrieval index/provider: not documented by the vendor",
        "Query fan-out and rewrite behaviour: undocumented",
        "Crawler/user-agent names and robots controls: undocumented",
        "Citation presentation (inline, cards, or absent): undocumented",
      ];
    case "partially_documented":
      return [
        "Query fan-out behaviour: only partly documented and mode-dependent",
        "Selection/reranking between retrieval and citation: not established",
        "Crawler/user-agent controls: only partly documented",
      ];
    case "documented_in_part":
      return [
        "Which consumer modes use which retrieval path: only partly documented",
        "Selection/reranking detail: not published in full",
      ];
    case "heterogeneous":
      return [
        "Behaviour varies by underlying bot/model — no single retrieval description applies",
        "Trigger, fan-out and citation behaviour are mode-dependent",
      ];
    default:
      return ["Retrieval behaviour: not yet assessed"];
  }
}

/** Registry statuses that mean retrieval architecture is genuinely unknown. */
export const RETRIEVAL_UNKNOWN_STATUSES = new Set(["under_documented", "heterogeneous"]);

/**
 * Everything the issue requires to be searchable: surface, vendor, family,
 * region and retrieval status — plus type, tier and distribution so a search
 * for "China" or "Baidu" behaves the way an analyst expects.
 */
export function buildHaystack(surface: RegistrySurface, lastReviewed: string): string {
  return [
    surface.id,
    surface.name,
    surface.vendor,
    surface.family,
    surface.type,
    label(TYPE_LABELS, surface.type),
    surface.tier,
    label(TIER_LABELS, surface.tier),
    ...(surface.regions ?? []),
    ...(surface.regions ?? []).map((r) => label(REGION_LABELS, r)),
    ...(surface.distribution ?? []),
    ...(surface.discovery_modes ?? []),
    surface.retrieval_status,
    label(RETRIEVAL_STATUS_LABELS, surface.retrieval_status),
    ...retrievalUnknowns(surface.retrieval_status),
    lastReviewed,
    "not yet ingested",
    "unknown",
  ]
    .join(" ")
    .toLowerCase();
}

/**
 * Projects registry entries into observation-plane rows. Registry facts are
 * kept verbatim; evidence fields carry only lightweight summary state — the
 * full claim/provenance payload is loaded lazily by the drill-down so the
 * client prop for the collapsed table stays bounded.
 */
export function toSurfaceRows(registry: Registry): SurfaceRow[] {
  const lastReviewed = registry.lastReviewed;
  return registry.surfaces.map((surface) => ({
    id: surface.id,
    name: surface.name,
    vendor: surface.vendor,
    family: surface.family,
    type: surface.type,
    typeLabel: label(TYPE_LABELS, surface.type),
    tier: surface.tier,
    tierLabel: label(TIER_LABELS, surface.tier),
    priorityRank: TIER_PRIORITY[surface.tier] ?? 99,
    regions: surface.regions ?? [],
    regionLabels: (surface.regions ?? []).map((r) => label(REGION_LABELS, r)),
    distribution: surface.distribution ?? [],
    distributionLabels: (surface.distribution ?? []).map((d) => titleise(d)),
    discoveryModes: surface.discovery_modes ?? [],
    discoveryModeLabels: (surface.discovery_modes ?? []).map((d) => titleise(d)),
    retrievalStatus: surface.retrieval_status,
    retrievalStatusLabel: label(RETRIEVAL_STATUS_LABELS, surface.retrieval_status),
    retrievalUnknown: RETRIEVAL_UNKNOWN_STATUSES.has(surface.retrieval_status),
    retrievalUnknownNotes: retrievalUnknowns(surface.retrieval_status),
    officialUrls: surface.official_urls ?? [],
    evidenceStatus: "no_evidence",
    evidenceLabel: "No evidence",
    evidenceNote: "No validated claim is linked to this surface yet.",
    confidenceLabel: "Unknown — no validated claim",
    freshnessLabel: "No capture yet",
    evidenceClaimCount: 0,
    lastReviewed,
    searchHaystack: buildHaystack(surface, lastReviewed),
  }));
}

/** Facet helper: tidy multi-value counts into a sorted list. */
export function facetEntries(values: Map<unknown, number>): Array<{ value: string; count: number }> {
  return [...values.entries()]
    .map(([value, count]) => ({ value: String(value), count }))
    .sort((a, b) => a.value.localeCompare(b.value));
}
