import { isDeepStrictEqual } from "node:util";

const banned = /\b(?:hash(?:es)?|claim[ -]ids?|confidence|corp(?:us|ora)|ledger|provenance|pipeline|ingestion|embeddings?|retrieval taxonomy)\b/i;
const unknown = /\b(?:unknown|unclear|undocumented|not known|not (?:publicly )?documented|no (?:public )?(?:information|documentation))\b/i;
const mechanicLabels = [
  "When it searches", "Where results come from", "Crawlers", "Keeping a page out",
  "Shopping", "Ads", "Measurement",
];

function requireGate(pass, reason) {
  if (!pass) throw new Error(reason);
}

function keys(object, required, optional = []) {
  return object && typeof object === "object" && !Array.isArray(object)
    && required.every((key) => Object.hasOwn(object, key))
    && Object.keys(object).every((key) => required.includes(key) || optional.includes(key));
}

export function sourceUrl(value) {
  const url = new URL(value);
  requireGate(url.protocol === "https:" && !url.port && !url.username && !url.password
    && /^(?:[a-z0-9-]+\.)+[a-z][a-z0-9-]+$/.test(url.hostname)
    && value === value.trim() && !url.hash, "source URL must be public HTTPS");
  return url;
}

function length(array, min, max, section) {
  requireGate(Array.isArray(array) && array.length >= min && array.length <= max,
    `schema or length budget at ${section}`);
}

function checkedDate(value) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const date = new Date(value);
  return !Number.isNaN(+date) && date.toISOString().slice(0, 10) === value;
}

export function validateGuide(guide, previous, verified, allowed, requiredRechecks, today) {
  const fields = ["name", "vendor", "region", "summary", "actions", "mechanics", "changes", "sources"];
  requireGate(keys(guide, fields, ["attributions"]), "guide schema");
  const statements = new Map();
  function prose(path, value, max) {
    requireGate(typeof value === "string" && value.trim() && value.length <= max,
      `schema or length budget at ${path}`);
    statements.set(path, value);
  }
  for (const field of ["name", "vendor", "region"]) {
    prose(field, guide[field], 80);
    requireGate(!previous || guide[field] === previous[field], `cannot change guide identity at ${field}`);
    statements.delete(field);
  }
  prose("summary", guide.summary, 350);
  length(guide.actions, 3, 5, "actions");
  guide.actions.forEach((row, i) => {
    requireGate(keys(row, ["title", "description"]), "action schema");
    prose(`actions.${i}.title`, row.title, 105);
    prose(`actions.${i}.description`, row.description, 260);
  });
  length(guide.mechanics, 7, 7, "mechanics");
  guide.mechanics.forEach((row, i) => {
    const path = `mechanics.${i}`;
    requireGate(row?.label === mechanicLabels[i], "mechanics labels and order");
    if (keys(row, ["label", "undocumented"]) && row.undocumented === true) {
      statements.set(`${path}.undocumented`, true);
    } else if (keys(row, ["label", "crawlers"]) && i === 2) {
      length(row.crawlers, 1, 8, `${path}.crawlers`);
      row.crawlers.forEach((crawler, j) => {
        requireGate(keys(crawler, ["userAgent", "purpose", "blocked"]), "crawler schema");
        for (const [field, budget] of Object.entries({ userAgent: 80, purpose: 100, blocked: 180 })) {
          prose(`${path}.crawlers.${j}.${field}`, crawler[field], budget);
        }
      });
    } else {
      requireGate(keys(row, ["label", "description"]), "mechanics schema");
      prose(`${path}.description`, row.description, 320);
    }
  });
  length(guide.changes, 1, 5, "changes");
  guide.changes.forEach((row, i) => {
    requireGate(keys(row, ["date", "change", "why"]), "change schema");
    for (const [field, budget] of Object.entries({ date: 48, change: 180, why: 180 })) {
      prose(`changes.${i}.${field}`, row[field], budget);
    }
  });

  length(guide.sources, 1, 12, "sources");
  const sources = new Map();
  for (const row of guide.sources) {
    requireGate(keys(row, ["title", "url", "checked"]), "source schema");
    requireGate(typeof row.title === "string" && row.title.trim() && row.title.length <= 160
      && !banned.test(row.title), "source title or length budget");
    sourceUrl(row.url);
    requireGate(allowed.has(row.url) && !sources.has(row.url), "unexpected or duplicate source URL");
    requireGate(checkedDate(row.checked) && row.checked <= today, "invalid source check date");
    const before = previous?.sources.find(({ url }) => url === row.url);
    const checkedNow = row.checked === today && verified.has(row.url);
    requireGate(isDeepStrictEqual(before, row) || checkedNow, "modified source must be re-fetched and dated today");
    requireGate(!requiredRechecks.has(row.url) || checkedNow, "due source was not re-fetched and dated today");
    sources.set(row.url, checkedNow);
  }

  const attribution = Object.hasOwn(guide, "attributions") ? guide.attributions : {};
  requireGate(attribution && typeof attribution === "object" && !Array.isArray(attribution), "attribution schema");
  for (const [path, urls] of Object.entries(attribution)) {
    requireGate(statements.has(path) && Array.isArray(urls) && urls.length > 0
      && new Set(urls).size === urls.length && urls.every((url) => sources.has(url)), `invalid attribution for ${path}`);
  }
  for (const [path, value] of statements) {
    const oldValue = path.split(".").reduce((value, key) => value?.[key], previous);
    const oldAttribution = previous?.attributions?.[path];
    if (value === oldValue && isDeepStrictEqual(attribution[path], oldAttribution)) continue;
    if (typeof value === "string") {
      const withoutUnknown = value.replaceAll(`Not documented by ${guide.vendor}`, "");
      requireGate(!banned.test(value) && !unknown.test(withoutUnknown), `editorial wording at ${path}`);
    }
    requireGate(attribution[path]?.length && attribution[path].every((url) => sources.get(url)),
      `new or changed statement requires freshly checked attribution at ${path}`);
  }
}
