import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { parse } from "yaml";

export type Crawler = {
  userAgent: string;
  purpose: string;
  blocked: string;
};

type Mechanic = { label: string } & (
  | { description: string }
  | { undocumented: true }
  | { crawlers: Crawler[] }
);

export type SurfaceGuide = {
  name: string;
  vendor: string;
  region: string;
  summary: string;
  actions: { title: string; description: string }[];
  mechanics: Mechanic[];
  changes: { date: string; change: string; why: string }[];
  sources: { title: string; url: string; checked: string }[];
};

const directory = path.join(process.cwd(), "content", "surfaces");

export function loadSurfaceGuides(): Map<string, SurfaceGuide> {
  return new Map(
    readdirSync(directory)
      .filter((file) => file.endsWith(".yaml"))
      .map((file) => [
        path.basename(file, ".yaml"),
        parse(readFileSync(path.join(directory, file), "utf8")) as SurfaceGuide,
      ]),
  );
}

export function formatCheckedDate(date: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(date));
}
