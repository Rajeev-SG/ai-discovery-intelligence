const day = 86_400_000;
const strongTopics = new Set([
  "crawler_index_policy", "commerce_ads", "measurement", "referrals_conversion",
]);
const official = new Set(["official", "press_release", "vendor_blog"]);
const allTopics = new Set([...strongTopics, "retrieval_index", "citations_sources", "optimisation_implication"]);

function captureKey(value) {
  const url = new URL(value);
  url.hash = "";
  if (url.pathname !== "/") url.pathname = url.pathname.replace(/\/$/, "");
  for (const key of [...url.searchParams.keys()]) {
    if (/^(?:utm_|ref$|fbclid$|gclid$)/i.test(key)) url.searchParams.delete(key);
  }
  url.searchParams.sort();
  return url.href;
}

export function planGuide(slug, guide, since, data, now) {
  const ids = slug === "google-ai-search" ? ["google-ai-mode", "google-ai-overviews"] : [slug];
  const relevant = (row) => ids.some((id) => row.surfaces.includes(id));
  const afterWrite = (row) => Date.parse(row.at) >= Date.parse(since);
  const claims = data.claims.filter(relevant);
  const newClaims = claims.filter(afterWrite);
  const events = data.events.filter(relevant).filter(afterWrite);
  const recheck = new Set();
  const changed = [];
  const urls = new Map((guide?.sources ?? []).map(({ url }) => [captureKey(url), url]));
  for (const { url } of claims) {
    const key = captureKey(url);
    if (!urls.has(key)) urls.set(key, url);
  }
  for (const [key, url] of urls) {
    const captures = data.captures.filter((row) => captureKey(row.url) === key);
    const latest = captures[0];
    const before = captures.find((row) => !afterWrite(row));
    const source = guide?.sources.find((row) => row.url === url);
    if (latest && before && afterWrite(latest) && latest.hash !== before.hash) {
      changed.push({ url, statement: latest.statement });
      if (source) recheck.add(url);
    }
    if (source && now - Date.parse(source.checked) >= 30 * day) recheck.add(url);
  }
  const support = claims.filter((row) => official.has(row.class) && row.status === "current"
    && row.url.startsWith("https:") && allTopics.has(row.topic));
  const topics = new Set(support.map(({ topic }) => topic));
  const canPromote = new Set(support.map(({ url }) => captureKey(url))).size >= 2
    && topics.size >= 3 && [...topics].some((topic) => strongTopics.has(topic));
  const hasSignal = newClaims.length || events.length || changed.length || recheck.size;
  if (!hasSignal || (!guide && !canPromote)) return null;
  const evidence = guide ? newClaims : support;
  return {
    recheck,
    evidence: {
      claims: evidence.map(({ url, class: authority, topic, status, statement }) =>
        ({ url, authority, topic, status, statement })),
      events: events.map(({ urls, type, statement }) => ({ urls, type, statement })),
      changed,
    },
  };
}
