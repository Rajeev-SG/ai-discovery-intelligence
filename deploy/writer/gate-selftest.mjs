// Offline proof that the content gate accepts a correct edit and rejects each
// class of bad one. No model, no network, no writes. Run it from the repo root:
//
//   ADI_WRITER_CHECKOUT=$PWD ADI_WRITER_YAML=$PWD/web/package.json \
//     node deploy/writer/gate-selftest.mjs
//
// The writer runs the same validateGuide on every real proposal, so a failure
// here means a real proposal would be judged the same way.
import fs from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { validateGuide } from "./writer-gates.mjs";

const checkout = process.env.ADI_WRITER_CHECKOUT ?? "/opt/adi-writer/checkout";
const require = createRequire(process.env.ADI_WRITER_YAML ?? path.join(checkout, "web/package.json"));
const { parse } = require("yaml");

const prev = parse(fs.readFileSync(path.join(checkout, "web/content/surfaces/chatgpt.yaml"), "utf8"));
const today = new Date().toISOString().slice(0, 10);
const urls = new Set(prev.sources.map(({ url }) => url));
const first = prev.sources[0].url;
const clone = () => structuredClone(prev);

// Swap one listed source's check date to today so a change may rely on it.
const rechecked = (guide) => ({
  ...guide,
  sources: guide.sources.map((row, i) => (i === 0 ? { ...row, checked: today } : row)),
});

const cases = [
  ["unchanged guide is accepted",
    () => validateGuide(clone(), prev, new Set(), urls, new Set(), today), true],
  ["attributed change on a freshly fetched source is accepted", () => {
    const guide = clone();
    guide.summary = prev.summary;
    guide.attributions = { summary: [first] };
    return validateGuide(rechecked(guide), prev, new Set([first]), urls, new Set(), today);
  }, true],
  ["changed statement with no attribution is rejected", () => {
    const guide = clone();
    guide.summary = "A different summary that nobody sourced.";
    return validateGuide(guide, prev, new Set(), urls, new Set(), today);
  }, false],
  ["attribution without a fresh fetch is rejected", () => {
    const guide = clone();
    guide.summary = "Another changed summary sentence.";
    guide.attributions = { summary: [first] };
    return validateGuide(guide, prev, new Set(), urls, new Set(), today);
  }, false],
  ["over-budget summary is rejected", () => {
    const guide = clone();
    guide.summary = "x".repeat(351);
    guide.attributions = { summary: [first] };
    return validateGuide(rechecked(guide), prev, new Set([first]), urls, new Set(), today);
  }, false],
  ["banned pipeline vocabulary is rejected", () => {
    const guide = clone();
    guide.summary = "The claim ledger is a media buying channel.";
    guide.attributions = { summary: [first] };
    return validateGuide(rechecked(guide), prev, new Set([first]), urls, new Set(), today);
  }, false],
  ["a source that is not on the list is rejected", () => {
    const guide = clone();
    guide.sources = [...guide.sources, { title: "Unlisted", url: "https://example.com/x", checked: "2026-01-01" }];
    return validateGuide(guide, prev, new Set(), urls, new Set(), today);
  }, false],
];

let failed = 0;
for (const [name, run, shouldPass] of cases) {
  let passed = true;
  let reason = "";
  try {
    run();
  } catch (error) {
    passed = false;
    reason = error.message;
  }
  const ok = passed === shouldPass;
  if (!ok) failed += 1;
  console.log(`${ok ? "ok  " : "FAIL"} ${name}${reason && !shouldPass ? ` — ${reason}` : ""}`);
}
if (failed) {
  console.error(`${failed} gate self-test case(s) failed`);
  process.exitCode = 1;
} else {
  console.log(`gate self-test passed (${cases.length} cases)`);
}
