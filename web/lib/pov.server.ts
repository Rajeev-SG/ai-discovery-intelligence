import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import generated from "./generated-pov.json";
import { projectPov, type PovView } from "./pov";

/**
 * Server-only POV loader. Kept separate from `@/lib/pov` (which is pure and
 * client-safe) because it touches `node:fs`, `node:path` and the environment.
 *
 * The committed artifact (`web/lib/generated-pov.json`) is the product read
 * contract: it is kept current by CI, so local dev and the deployed `web/`-root
 * build (Vercel, where `../pov` is absent) read the same data. We deliberately
 * do not read `pov/state.yaml` here — re-deriving confidence in TypeScript would
 * fork the deterministic gate, and the artifact is the tested project of it.
 */

/** The canonical committed artifact path, relative to the `web/` project root. */
export const ARTIFACT_PATH = path.join(process.cwd(), "lib", "generated-pov.json");

/**
 * Load the POV product view.
 *
 * Precedence:
 *  1. `POV_PATH` — an explicit override pointing at a generated JSON artifact.
 *     When set, the file must exist and parse: a typo or a corrupt override
 *     must fail loudly rather than silently serving stale data.
 *  2. the committed `web/lib/generated-pov.json` imported at build time.
 */
export function loadPov(): PovView {
  const override = process.env.POV_PATH;
  if (override) {
    if (!existsSync(override)) {
      throw new Error(`POV_PATH is set but the file does not exist: ${override}`);
    }
    let parsed: unknown;
    try {
      parsed = JSON.parse(readFileSync(override, "utf8"));
    } catch (error) {
      throw new Error(
        `POV_PATH is set but the file could not be parsed as JSON: ${override} (${String(error)})`,
      );
    }
    return projectPov(parsed);
  }
  return projectPov(generated);
}
