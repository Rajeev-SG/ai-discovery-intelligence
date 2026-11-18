import Link from "next/link";
import { Fragment } from "react";
import registry from "@/lib/generated-registry.json";
import comingSoonReasons from "@/content/coming-soon.json";
import { formatCheckedDate, type Crawler, type SurfaceGuide } from "@/lib/surface-guides";
import { SurfacePicker } from "./surface-picker";
import styles from "./surface-field-guide.module.css";

const featured = [
  { slug: "chatgpt", name: "ChatGPT" },
  { slug: "google-ai-search", name: "Google AI Overviews & AI Mode" },
  { slug: "google-gemini", name: "Gemini" },
  { slug: "perplexity", name: "Perplexity" },
  { slug: "microsoft-copilot", name: "Copilot" },
  { slug: "meta-ai", name: "Meta AI" },
];

const coveredByGoogleGuide = new Set(["google-ai-overviews", "google-ai-mode"]);

function SurfaceSwitcher({
  slug,
  guides,
}: {
  slug?: string;
  guides: Map<string, SurfaceGuide>;
}) {
  const listed = new Set(featured.map((surface) => surface.slug));
  const published = [...guides]
    .filter(([id]) => !listed.has(id))
    .map(([id, guide]) => ({ slug: id, name: guide.name }));
  const comingSoon = registry.surfaces.filter(
    ({ id }) => !guides.has(id) && !coveredByGoogleGuide.has(id),
  );
  const reasons: Readonly<Record<string, string>> = comingSoonReasons;
  const choices = [...featured, ...published].filter(({ slug: id }) => guides.has(id));

  return (
    <nav className={styles.switcher} aria-label="AI surfaces">
      <SurfacePicker
        slug={slug}
        published={choices}
        comingSoon={comingSoon.map(({ id, name }) => ({ slug: id, name }))}
      />
      <div className={styles.pillList}>
        {choices.map(({ slug: id, name }) => (
          <Link key={id} className={styles.pill} href={`/surfaces/${id}`} aria-current={id === slug ? "page" : undefined}>
            {name}
          </Link>
        ))}
        {comingSoon.length > 0 && (
          <details className={styles.more}>
            <summary className={styles.pill}>Coming soon</summary>
            <ul>
              {comingSoon.map(({ id, name }) => (
                <li key={id}>{name}<small>{reasons[id]}</small></li>
              ))}
            </ul>
          </details>
        )}
      </div>
    </nav>
  );
}

export function SurfaceDirectory({ guides }: { guides: Map<string, SurfaceGuide> }) {
  return (
    <div className={styles.page}>
      <div className={styles.shell}>
        <h1 className={styles.intro}>Where brands show up in AI answers, shopping recommendations and ads.</h1>
        <SurfaceSwitcher guides={guides} />
      </div>
    </div>
  );
}

function InlineText({ text }: { text: string }) {
  return text.split(/(`[^`]+`)/).map((part, index) =>
    part.startsWith("`") ? <code key={index}>{part.slice(1, -1)}</code> : <Fragment key={index}>{part}</Fragment>,
  );
}

function CrawlerTable({ crawlers }: { crawlers: Crawler[] }) {
  return (
    <table className={styles.crawlers} aria-label="Crawlers">
      <thead>
        <tr>
          <th scope="col">User agent</th>
          <th scope="col">Used for</th>
          <th scope="col">If you block it</th>
        </tr>
      </thead>
      <tbody>
        {crawlers.map(({ userAgent, purpose, blocked }) => (
          <tr key={userAgent}>
            <th scope="row">{userAgent}</th>
            <td>{purpose}</td>
            <td>{blocked}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function SurfaceFieldGuide({
  slug,
  guide,
  guides,
}: {
  slug: string;
  guide: SurfaceGuide;
  guides: Map<string, SurfaceGuide>;
}) {
  const { name, vendor, region, summary, actions, mechanics, changes, sources } = guide;
  const checked = sources.map((source) => source.checked).sort()[0];

  return (
    <div className={styles.page}>
      <div className={styles.shell}>
        <SurfaceSwitcher slug={slug} guides={guides} />
        <article className={styles.article}>
          <header className={styles.header}>
            <p className={styles.vendor}>{vendor} · {region}</p>
            <h1>{name}</h1>
            <p className={styles.summary}>{summary}</p>
            <p className={styles.checked}>Sources checked <time dateTime={checked}>{formatCheckedDate(checked)}</time></p>
          </header>

          <section className={styles.actions}>
            <h2>What to do</h2>
            <ol role="list">
              {actions.map(({ title, description }, index) => (
                <li key={title}>
                  <span className={styles.number} aria-hidden="true">{index + 1}</span>
                  <div>
                    <p className={styles.actionTitle}>{title}</p>
                    <p><InlineText text={description} /></p>
                  </div>
                </li>
              ))}
            </ol>
          </section>

          <section className={styles.mechanics}>
            <h2>How it works</h2>
            <dl>
              {mechanics.map((row) => (
                <div key={row.label}>
                  <dt>{row.label}</dt>
                  <dd>
                    {"crawlers" in row ? <CrawlerTable crawlers={row.crawlers} />
                      : "undocumented" in row ? <span className={styles.undocumented}>Not documented by {vendor}.</span>
                      : <InlineText text={row.description} />}
                  </dd>
                </div>
              ))}
            </dl>
          </section>

          <section className={styles.changes}>
            <h2>Recent changes that matter</h2>
            <ul role="list">
              {changes.map(({ date, change, why }) => (
                <li key={change}>
                  <span className={styles.changeDate}>{date}</span>
                  <p>{change} <span className={styles.changeWhy}>{why}</span></p>
                </li>
              ))}
            </ul>
          </section>

          <footer className={styles.sources}>
            <h2>Sources · checked <time dateTime={checked}>{formatCheckedDate(checked)}</time></h2>
            {sources.map(({ title, url, checked: sourceChecked }) => (
              <div key={url}>
                <a href={url}>{title}</a>
                {sourceChecked !== checked && <> · <time dateTime={sourceChecked}>{formatCheckedDate(sourceChecked)}</time></>}
              </div>
            ))}
          </footer>
        </article>
      </div>
    </div>
  );
}
