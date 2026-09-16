/**
 * URL state for the observation plane. Only meaningful, shareable state is
 * persisted: search, sorting, column filters, expanded rows and visible
 * columns. Everything else stays out of the URL.
 */
export interface PlaneUrlState {
  q: string;
  sort: Array<{ id: string; desc: boolean }>;
  filters: Record<string, string[]>;
  expanded: string[];
  cols: string[];
}

export const EMPTY_URL_STATE: PlaneUrlState = {
  q: "",
  sort: [],
  filters: {},
  expanded: [],
  cols: [],
};

function parsePairs(raw: string | null): Array<{ id: string; desc: boolean }> {
  if (!raw) return [];
  return raw
    .split(",")
    .map((entry) => entry.trim())
    .filter(Boolean)
    .map((entry) => {
      const [id, dir] = entry.split(":");
      return { id, desc: dir === "desc" };
    })
    .filter((entry) => Boolean(entry.id));
}

export function encodeUrlState(state: PlaneUrlState): string {
  const params = new URLSearchParams();
  if (state.q.trim()) params.set("q", state.q.trim());
  if (state.sort.length) {
    params.set("sort", state.sort.map((s) => `${s.id}:${s.desc ? "desc" : "asc"}`).join(","));
  }
  for (const [id, values] of Object.entries(state.filters)) {
    if (values.length) params.set(`f_${id}`, [...values].sort().join("|"));
  }
  if (state.expanded.length) params.set("expanded", [...state.expanded].sort().join(","));
  if (state.cols.length) params.set("cols", state.cols.join(","));
  return params.toString();
}

export function decodeUrlState(params: URLSearchParams | Record<string, string | string[] | undefined>): PlaneUrlState {
  const get = (key: string): string | null => {
    if (params instanceof URLSearchParams) return params.get(key);
    const value = params[key];
    if (Array.isArray(value)) return value[0] ?? null;
    return value ?? null;
  };
  const keys = params instanceof URLSearchParams ? [...params.keys()] : Object.keys(params);
  const filters: Record<string, string[]> = {};
  for (const key of keys) {
    if (!key.startsWith("f_")) continue;
    const raw = get(key);
    if (!raw) continue;
    const values = raw.split("|").map((v) => v.trim()).filter(Boolean);
    if (values.length) filters[key.slice(2)] = values;
  }
  return {
    q: get("q") ?? "",
    sort: parsePairs(get("sort")),
    filters,
    expanded: (get("expanded") ?? "")
      .split(",")
      .map((v) => v.trim())
      .filter(Boolean),
    cols: (get("cols") ?? "")
      .split(",")
      .map((v) => v.trim())
      .filter(Boolean),
  };
}

export function isPristine(state: PlaneUrlState): boolean {
  return encodeUrlState(state) === "";
}
